"""
Motor de IA usando LiteLLM — proveedor configurable por .env.
Proveedores soportados: gemini (Gemini API), anthropic (Claude).

Genera análisis narrativos para los informes 3 y 4.
Todos los prompts están en español y producen texto listo para
pegar en el .docx institucional.

Manejo de errores: reintentos con backoff exponencial.
Si falla tras N intentos, devuelve texto de fallback genérico.
"""

import json
import os
import re
import time
import statistics
from typing import Any
from loguru import logger
import litellm
from app.core.config import settings

litellm.set_verbose = False
# Sin esto litellm imprime "Give Feedback / Get Help..." en cada excepción
# (cada rate limit), y ensucia el log
litellm.suppress_debug_info = True

MAX_REINTENTOS = 5
DELAY_BASE_SEG = 2.0  # espera exponencial: 2, 4, 8, 16 seg
# Tokens extra para modelos que razonan (gpt-oss). Con reasoning_effort=low el
# razonamiento ronda los 100-250 tokens. No subirlo de más: Groq descuenta
# max_tokens completo del límite por minuto aunque no se usen.
MARGEN_RAZONAMIENTO = 500


def _api_key_y_modelo() -> tuple[str | None, str]:
    """Devuelve (api_key_o_None, model_id) según el proveedor configurado."""
    proveedor = settings.AI_PROVIDER.lower()
    modelo = settings.AI_MODEL

    if proveedor == "gemini":
        # LiteLLM lee GEMINI_API_KEY del entorno automáticamente
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        if not modelo.startswith("gemini/"):
            modelo = f"gemini/{modelo}"
        # Para Gemini API no pasamos api_key directamente — LiteLLM lo toma del env
        return None, modelo

    if proveedor == "deepseek":
        # LiteLLM lee DEEPSEEK_API_KEY del entorno automáticamente
        os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
        if not modelo.startswith("deepseek/"):
            modelo = f"deepseek/{modelo}"
        return settings.DEEPSEEK_API_KEY, modelo

    if proveedor == "groq":
        # LiteLLM lee GROQ_API_KEY del entorno automáticamente
        os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
        if not modelo.startswith("groq/"):
            modelo = f"groq/{modelo}"
        return settings.GROQ_API_KEY, modelo

    if proveedor == "openai":
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        if not modelo.startswith("openai/"):
            modelo = f"openai/{modelo}"
        return settings.OPENAI_API_KEY, modelo

    # Anthropic
    modelo_anthropic = modelo if modelo.startswith("anthropic/") else f"anthropic/{modelo}"
    return settings.ANTHROPIC_API_KEY, modelo_anthropic


def _api_configurada() -> bool:
    proveedor = settings.AI_PROVIDER.lower()
    if proveedor == "gemini":
        return bool(settings.GEMINI_API_KEY)
    if proveedor == "deepseek":
        return bool(settings.DEEPSEEK_API_KEY)
    if proveedor == "groq":
        return bool(settings.GROQ_API_KEY)
    if proveedor == "openai":
        return bool(settings.OPENAI_API_KEY)
    return bool(settings.ANTHROPIC_API_KEY) and settings.ANTHROPIC_API_KEY != "sk-ant-REEMPLAZAR"


def _es_razonador_openai(modelo: str) -> bool:
    """gpt-5*, o1*, o3*, o4* — modelos de OpenAI que razonan antes de responder."""
    nombre = modelo.removeprefix("openai/")
    return bool(re.match(r"(gpt-5|o\d)", nombre))


def _llamar_ia(prompt: str, max_tokens: int = 800) -> str:
    """
    Llama a LiteLLM con reintentos y backoff exponencial.
    Devuelve el texto generado o un mensaje de fallback.
    """
    if not _api_configurada():
        logger.warning(f"API key de IA ({settings.AI_PROVIDER}) no configurada — devolviendo placeholder")
        return f"[Análisis pendiente: configure {settings.AI_PROVIDER.upper()}_API_KEY en el archivo .env]"

    api_key, modelo = _api_key_y_modelo()

    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            kwargs: dict = {
                "model": modelo,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            }
            if api_key:  # None para Gemini (usa env var GEMINI_API_KEY)
                kwargs["api_key"] = api_key
            # Los modelos gpt-oss razonan antes de responder y ese razonamiento
            # consume max_tokens: con 800 la respuesta llegaba vacía. Se pide
            # razonamiento corto y se da margen extra para el texto.
            if "gpt-oss" in modelo:
                kwargs["reasoning_effort"] = "low"
                kwargs["max_tokens"] = max_tokens + MARGEN_RAZONAMIENTO
            # Modelos de razonamiento de OpenAI (gpt-5*, o1/o3/o4*): no aceptan
            # max_tokens sino max_completion_tokens, y también razonan antes de
            # responder. Se manda por extra_body para que litellm no lo filtre
            # aunque no conozca el modelo.
            elif _es_razonador_openai(modelo):
                del kwargs["max_tokens"]
                kwargs["max_completion_tokens"] = max_tokens + MARGEN_RAZONAMIENTO
                kwargs["extra_body"] = {"reasoning_effort": "low"}
            # Qwen3 en Groq: con el razonamiento apagado responde directo, como
            # llama, sin gastar tokens del límite por minuto en "pensar".
            elif "qwen3" in modelo:
                kwargs["reasoning_effort"] = "none"
            respuesta = litellm.completion(**kwargs)
            texto = (respuesta.choices[0].message.content or "").strip()
            # Por si algún modelo deja su razonamiento dentro del texto
            texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL).strip()
            if not texto:
                motivo = respuesta.choices[0].finish_reason
                raise ValueError(f"respuesta vacía de la IA (finish_reason={motivo})")
            logger.debug(f"IA respondió ({len(texto)} chars) en intento {intento}")
            return texto
        except Exception as e:
            msg = str(e)
            msg_min = msg.lower()
            logger.warning(f"Error IA intento {intento}/{MAX_REINTENTOS}: {msg[:200]}")
            # Groq no siempre incluye "429" en el texto: se detecta también por
            # la clase de la excepción y por "rate limit".
            es_rate_limit = (
                isinstance(e, litellm.RateLimitError)
                or "429" in msg
                or "rate limit" in msg_min
            )
            # Cuota DIARIA agotada (Groq: "tokens per day (TPD)"): reintentar no sirve
            if es_rate_limit and ("per day" in msg_min or "(tpd)" in msg_min or "(rpd)" in msg_min):
                logger.error("Cuota diaria de IA agotada — usando fallback sin reintentos")
                break
            # Cuenta sin saldo (OpenAI: "insufficient_quota" / "no credits"). También
            # llega como 429, pero esperar no lo arregla: hay que cargar saldo.
            if "insufficient_quota" in msg_min or "credits" in msg_min or "billing" in msg_min:
                logger.error("La cuenta del proveedor de IA no tiene saldo — usando fallback sin reintentos")
                break
            if intento < MAX_REINTENTOS:
                espera = DELAY_BASE_SEG * (2 ** (intento - 1))
                if es_rate_limit:
                    # Límite por minuto: Groq dice cuánto esperar ("try again in 7.5s")
                    sugerida = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", msg_min)
                    if sugerida:
                        espera = int(sugerida.group(1) or 0) * 60 + float(sugerida.group(2)) + 1
                    else:
                        espera = max(espera, 20)
                time.sleep(espera)

    logger.error("IA falló tras todos los reintentos — usando fallback")
    return "[Análisis no disponible — la IA no respondió. Editar manualmente este campo.]"


# ──────────────────────────────────────────────────────────────────
# Cálculo de estadísticos (sin IA)
# ──────────────────────────────────────────────────────────────────

def calcular_estadisticos_interciclo(estudiantes: list[dict]) -> dict:
    """Calcula estadísticos del Parcial 1 (sobre 50 puntos)."""
    notas = [e["parcial1"] for e in estudiantes if e.get("parcial1") is not None]
    if not notas:
        return {}

    alto = sum(1 for n in notas if n >= 40)
    medio = sum(1 for n in notas if 30 <= n < 40)
    bajo = sum(1 for n in notas if n < 30)

    return {
        "total_estudiantes": len(notas),
        "maximo": round(max(notas), 2),
        "minimo": round(min(notas), 2),
        "promedio": round(statistics.mean(notas), 2),
        "mediana": round(statistics.median(notas), 2),
        "rango_alto": alto,
        "rango_medio": medio,
        "rango_bajo": bajo,
        "pct_alto": round(alto / len(notas) * 100, 1),
        "pct_medio": round(medio / len(notas) * 100, 1),
        "pct_bajo": round(bajo / len(notas) * 100, 1),
    }


def calcular_estadisticos_finales(estudiantes: list[dict]) -> dict:
    """Calcula estadísticos completos para el Informe 4."""
    def _notas(campo: str) -> list[float]:
        return [e[campo] for e in estudiantes if e.get(campo) is not None and e[campo] > 0]

    nf = _notas("nota_final")
    p1 = _notas("parcial1")
    p2 = _notas("parcial2")
    rec = _notas("recuperacion")

    aprobados = sum(1 for e in estudiantes if e.get("estado") == "APROBADO")
    reprobados = sum(1 for e in estudiantes if e.get("estado") == "REPROBADO")
    con_recuperacion = sum(1 for e in estudiantes if (e.get("recuperacion") or 0) > 0)

    def _stats(lista: list[float]) -> dict:
        if not lista:
            return {}
        return {
            "n": len(lista),
            "max": round(max(lista), 2),
            "min": round(min(lista), 2),
            "promedio": round(statistics.mean(lista), 2),
            "mediana": round(statistics.median(lista), 2),
            "desv_std": round(statistics.stdev(lista), 2) if len(lista) > 1 else 0,
        }

    return {
        "total_estudiantes": len(estudiantes),
        "aprobados": aprobados,
        "reprobados": reprobados,
        "pct_aprobacion": round(aprobados / len(estudiantes) * 100, 1) if estudiantes else 0,
        "con_recuperacion": con_recuperacion,
        "nota_final": _stats(nf),
        "parcial1": _stats(p1),
        "parcial2": _stats(p2),
        "recuperacion": _stats(rec),
    }


# ──────────────────────────────────────────────────────────────────
# Prompts — Informe 3 (Interciclo)
# ──────────────────────────────────────────────────────────────────

def analizar_calificaciones_interciclo(
    asignatura: str,
    grupo: str,
    docente: str,
    estadisticos: dict,
    estudiantes: list[dict],
) -> dict:
    """
    Genera análisis narrativo del Parcial 1 (sobre 50 puntos).
    Retorna dict con: analisis_narrativo, conclusion, acciones_mejora.
    """
    est = estadisticos
    notas_lista = sorted(
        [e["parcial1"] for e in estudiantes if e.get("parcial1") is not None]
    )

    prompt_narrativo = f"""Eres un analista académico de la Carrera de Computación de la Universidad Politécnica Salesiana (UPS) Cuenca, Ecuador.

Redacta un análisis narrativo del PRIMER PARCIAL (sobre 50 puntos) de la asignatura "{asignatura}", grupo {grupo}, docente {docente}.

DATOS ESTADÍSTICOS:
- Total de estudiantes evaluados: {est.get('total_estudiantes', 0)}
- Nota máxima: {est.get('maximo', 0)}/50
- Nota mínima: {est.get('minimo', 0)}/50
- Promedio: {est.get('promedio', 0)}/50
- Mediana: {est.get('mediana', 0)}/50
- Rango ALTO (≥40/50): {est.get('rango_alto', 0)} estudiantes ({est.get('pct_alto', 0)}%)
- Rango MEDIO (30-39/50): {est.get('rango_medio', 0)} estudiantes ({est.get('pct_medio', 0)}%)
- Rango BAJO (<30/50): {est.get('rango_bajo', 0)} estudiantes ({est.get('pct_bajo', 0)}%)
- Distribución de notas: {notas_lista[:20]}{"..." if len(notas_lista) > 20 else ""}

INSTRUCCIONES:
- Escribe 3-4 oraciones de análisis objetivo y profesional en español formal
- Menciona los rangos de distribución y qué indican sobre el rendimiento del grupo
- NO uses frases como "Es importante destacar" o "Es fundamental"
- Tono institucional, directo y analítico"""

    narrativo = _llamar_ia(prompt_narrativo, max_tokens=400)

    prompt_acciones = f"""Eres un analista académico de la UPS Cuenca.

Basándote en estos resultados del primer parcial de "{asignatura}" grupo {grupo}:
- Promedio: {est.get('promedio', 0)}/50
- Rango bajo (<30/50): {est.get('rango_bajo', 0)} de {est.get('total_estudiantes', 0)} estudiantes

Propón 2-3 acciones de mejora concretas y específicas para el docente {docente}.
Formato: lista numerada, cada acción en una sola oración. Español formal."""

    acciones = _llamar_ia(prompt_acciones, max_tokens=300)

    conclusion = (
        f"El grupo {grupo} de {asignatura} presenta un promedio de "
        f"{est.get('promedio', 0)}/50 en el primer parcial, con "
        f"{est.get('pct_bajo', 0)}% de estudiantes en rango bajo."
    )

    return {
        "analisis_narrativo": narrativo,
        "conclusion": conclusion,
        "acciones_mejora": acciones,
        **est,
    }


# ──────────────────────────────────────────────────────────────────
# Prompts — Informe 4 (Final)
# ──────────────────────────────────────────────────────────────────

CLAVES_FINALES = [
    "analisis_general",
    "distribucion_aprobacion",
    "comportamiento_notas_finales",
    "analisis_parcial1",
    "analisis_parcial2",
    "comparacion_parciales",
    "uso_recuperacion",
    "relacion_parciales_nota_final",
    "outliers",
    "patrones_generales",
    "acciones_mejora",
]


def _analisis_finales_combinado(
    contexto_base: str, est: dict, respuesta_docente: str, asignatura: str, grupo: str
) -> dict | None:
    """
    Pide los 11 textos del Informe 4 en una sola llamada, como JSON.
    Devuelve None si la respuesta no trae un JSON válido con todas las claves:
    el llamador usa entonces el método de una llamada por análisis.
    """
    nf = est.get("nota_final", {})
    p1 = est.get("parcial1", {})
    p2 = est.get("parcial2", {})
    contexto_docente = (
        f"\nEl docente respondió: \"{respuesta_docente[:500]}\"" if respuesta_docente else ""
    )
    prompt = f"""Eres analista académico de la UPS Cuenca. Redacta en español formal y objetivo.
{contexto_base}
NF — Desv. estándar: {nf.get('desv_std','—')}
P1 — Máx: {p1.get('max','—')} | Mín: {p1.get('min','—')}
P2 — Máx: {p2.get('max','—')} | Mín: {p2.get('min','—')}{contexto_docente}

Devuelve SOLO un objeto JSON (sin texto antes ni después, sin ```), con estas claves.
Cada valor es un texto de máximo 4 oraciones, sin frases de relleno, tono institucional directo:
- "analisis_general": análisis general del rendimiento del grupo en el período completo.
- "distribucion_aprobacion": distribución entre aprobados y reprobados y qué indica sobre el grupo.
- "comportamiento_notas_finales": comportamiento de las notas finales (promedio, máxima, mínima, desviación).
- "analisis_parcial1": desempeño en el Parcial 1.
- "analisis_parcial2": desempeño en el Parcial 2.
- "comparacion_parciales": comparación entre Parcial 1 y Parcial 2, si hubo mejora o retroceso.
- "uso_recuperacion": uso del examen de recuperación y su impacto.
- "relacion_parciales_nota_final": si los parciales predicen adecuadamente la nota final.
- "outliers": posibles valores atípicos según máxima, mínima y desviación estándar.
- "patrones_generales": patrones generales de rendimiento observados.
- "acciones_mejora": 3-4 acciones de mejora concretas para {asignatura} grupo {grupo}, como lista numerada en un solo texto (separadas por saltos de línea)."""

    texto = _llamar_ia(prompt, max_tokens=2500)
    # Si la IA no respondió (sin saldo, cuota diaria, etc.) no tiene sentido
    # reintentar con 11 llamadas más: se deja el fallback en todos los campos.
    if texto.startswith("[Análisis"):
        return {clave: texto for clave in CLAVES_FINALES}
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fin <= inicio:
        logger.warning("Informe 4: la respuesta combinada no trae JSON — se usa una llamada por análisis")
        return None
    try:
        datos = json.loads(texto[inicio:fin + 1], strict=False)
    except json.JSONDecodeError:
        logger.warning("Informe 4: JSON combinado inválido — se usa una llamada por análisis")
        return None

    resultado = {}
    for clave in CLAVES_FINALES:
        valor = datos.get(clave)
        if isinstance(valor, list):  # p. ej. acciones_mejora devuelta como lista
            valor = "\n".join(f"{i}. {v}" for i, v in enumerate(valor, 1))
        if not isinstance(valor, str) or not valor.strip():
            logger.warning(f"Informe 4: falta '{clave}' en el JSON combinado — se usa una llamada por análisis")
            return None
        resultado[clave] = valor.strip()
    # A veces la lista numerada llega en una sola línea ("1. … 2. …"):
    # cada acción va en su propia línea, como cuando se pedía por separado
    resultado["acciones_mejora"] = re.sub(r"\s+(?=\d+\.\s)", "\n", resultado["acciones_mejora"])
    return resultado


def analizar_calificaciones_finales(
    asignatura: str,
    grupo: str,
    docente: str,
    estadisticos: dict,
    estudiantes: list[dict],
    respuesta_docente: str = "",
) -> dict:
    """
    Genera los 10 sub-análisis narrativos del Informe 4.
    """
    est = estadisticos
    nf = est.get("nota_final", {})
    p1 = est.get("parcial1", {})
    p2 = est.get("parcial2", {})
    rec = est.get("recuperacion", {})

    contexto_base = f"""Asignatura: {asignatura} | Grupo: {grupo} | Docente: {docente}
Total estudiantes: {est.get('total_estudiantes', 0)}
Aprobados: {est.get('aprobados', 0)} ({est.get('pct_aprobacion', 0)}%) | Reprobados: {est.get('reprobados', 0)}
NF — Prom: {nf.get('promedio','—')} | Máx: {nf.get('max','—')} | Mín: {nf.get('min','—')}
P1 — Prom: {p1.get('promedio','—')} | P2 — Prom: {p2.get('promedio','—')}
Con recuperación: {est.get('con_recuperacion', 0)} estudiantes"""

    def _analisis(instruccion: str, tokens: int = 350) -> str:
        return _llamar_ia(
            f"""Eres analista académico de la UPS Cuenca. Redacta en español formal y objetivo.
{contexto_base}

{instruccion}

Máximo 4 oraciones. Sin frases de relleno. Tono institucional directo.""",
            max_tokens=tokens,
        )

    # Intento 1: los 11 textos en UNA sola llamada. Con límites de ~8000 tokens
    # por minuto (Groq gratis), 11 llamadas por asignatura reenviando el mismo
    # contexto hacían que un Informe 4 tardara casi una hora y agotara la cuota.
    combinado = _analisis_finales_combinado(contexto_base, est, respuesta_docente, asignatura, grupo)
    if combinado:
        return {**combinado, **est}

    # Intento 2 (fallback): una llamada por análisis, como antes
    analisis = {}

    analisis["analisis_general"] = _analisis(
        "Escribe un análisis general del rendimiento académico del grupo en el período completo."
    )
    analisis["distribucion_aprobacion"] = _analisis(
        f"Analiza la distribución entre aprobados ({est.get('aprobados',0)}) y reprobados ({est.get('reprobados',0)}). Interpreta qué indica sobre el grupo."
    )
    analisis["comportamiento_notas_finales"] = _analisis(
        f"Analiza el comportamiento de las notas finales: promedio {nf.get('promedio','—')}, máxima {nf.get('max','—')}, mínima {nf.get('min','—')}, desviación estándar {nf.get('desv_std','—')}."
    )
    analisis["analisis_parcial1"] = _analisis(
        f"Analiza el desempeño en el Parcial 1: promedio {p1.get('promedio','—')}, máximo {p1.get('max','—')}, mínimo {p1.get('min','—')}."
    )
    analisis["analisis_parcial2"] = _analisis(
        f"Analiza el desempeño en el Parcial 2: promedio {p2.get('promedio','—')}, máximo {p2.get('max','—')}, mínimo {p2.get('min','—')}."
    )
    analisis["comparacion_parciales"] = _analisis(
        f"Compara el rendimiento entre Parcial 1 (promedio {p1.get('promedio','—')}) y Parcial 2 (promedio {p2.get('promedio','—')}). ¿Hubo mejora o retroceso?"
    )
    analisis["uso_recuperacion"] = _analisis(
        f"Analiza el uso del examen de recuperación: {est.get('con_recuperacion',0)} de {est.get('total_estudiantes',0)} estudiantes lo tomaron. Interpreta su impacto."
    )
    analisis["relacion_parciales_nota_final"] = _analisis(
        "Analiza la relación entre los parciales y la nota final. ¿Los parciales predicen adecuadamente el resultado final?"
    )
    analisis["outliers"] = _analisis(
        f"Identifica posibles outliers en el grupo basándote en máxima ({nf.get('max','—')}), mínima ({nf.get('min','—')}) y desviación estándar ({nf.get('desv_std','—')})."
    )
    analisis["patrones_generales"] = _analisis(
        "Describe los patrones generales de rendimiento observados en este grupo durante el período."
    )

    # Acciones de mejora considerando respuesta del docente
    contexto_docente = (
        f"\nEl docente respondió: \"{respuesta_docente[:500]}\"" if respuesta_docente else ""
    )
    analisis["acciones_mejora"] = _llamar_ia(
        f"""Eres analista académico de la UPS Cuenca.
{contexto_base}{contexto_docente}
Propón 3-4 acciones de mejora concretas para la asignatura {asignatura} grupo {grupo}.
Formato: lista numerada. Cada acción: una oración específica y accionable. Español formal.""",
        max_tokens=400,
    )

    return {**analisis, **est}


# ──────────────────────────────────────────────────────────────────
# Análisis consolidado del área (Informe 4)
# ──────────────────────────────────────────────────────────────────

def analizar_consolidado_area(
    area: str,
    resumen_por_asignatura: list[dict],
) -> dict:
    """
    Genera el análisis consolidado del área y acciones generales.
    resumen_por_asignatura: [{"asignatura": str, "grupo": str, "pct_aprobacion": float, "promedio_nf": float}]
    """
    tabla = "\n".join(
        f"- {r['asignatura']} ({r['grupo']}): "
        f"{r.get('pct_aprobacion',0)}% aprobación, promedio NF {r.get('promedio_nf','—')}"
        for r in resumen_por_asignatura
    )

    consolidado = _llamar_ia(
        f"""Eres analista académico de la UPS Cuenca. Área: {area}.

Resumen de rendimiento por asignatura:
{tabla}

Redacta un análisis consolidado del área en 4-5 oraciones. Identifica tendencias
generales, asignaturas con mejor y peor rendimiento, y patrones comunes. Español formal.""",
        max_tokens=500,
    )

    acciones_generales = _llamar_ia(
        f"""Área: {area}. Resumen de rendimiento:
{tabla}

Propón 3-4 acciones de mejora generales para el área. Lista numerada, una oración por acción.
Acciones estratégicas aplicables a todo el equipo docente del área. Español formal.""",
        max_tokens=400,
    )

    return {
        "analisis_consolidado_area": consolidado,
        "acciones_generales_area": acciones_generales,
    }


# ──────────────────────────────────────────────────────────────────
# Prompts — Informe 2 (Revisión AVAC)
# ──────────────────────────────────────────────────────────────────

# Etiqueta legible de cada parámetro del checklist del aula virtual
PARAMETROS_AVAC: dict[str, str] = {
    "silabo_cargado": "Sílabo cargado",
    "registro_avance": "Registro de avance del sílabo",
    "guia_practicas": "Guía de componente práctico",
    "consejeria_academica": "Enlace de consejería académica",
    "recursos_derechos_autor": "Recursos con derechos de autor",
    "libros_digitales": "Libros digitales de biblioteca",
    "seccion_practicas": "Sección PRÁCTICAS",
    "guias_componente": "Guías de cada componente práctico",
    "actividades_con_rubrica": "Actividades calificadas con rúbrica",
    "seccion_investigativas": "Sección INVESTIGATIVAS",
    "actividad_investigacion": "Actividad para fomentar la investigación",
    "proyecto_integrador": "Proyecto integrador de materias",
}


def sugerir_acciones_avac(
    docente: str,
    asignatura: str,
    grupo: str,
    checks: dict[str, bool],
    observaciones: str = "",
) -> str:
    """
    Acciones de mejora sugeridas para el aula virtual (Informe 2).

    Se construyen a partir de los parámetros AVAC **incumplidos** y de las
    observaciones que escribió el jefe de área. Si todo está cumplido y no hay
    observaciones, no se llama a la IA: se devuelve un texto de mantenimiento.
    """
    incumplidos = [
        PARAMETROS_AVAC.get(campo, campo)
        for campo, valor in checks.items()
        if campo in PARAMETROS_AVAC and not valor
    ]

    if not incumplidos and not observaciones.strip():
        return (
            "El aula virtual cumple los doce parámetros evaluados. Se recomienda mantener "
            "la estructura actual y actualizar los recursos al inicio de cada período."
        )

    detalle_incumplidos = (
        "\n".join(f"- {p}" for p in incumplidos)
        if incumplidos
        else "- Ninguno: los doce parámetros están cumplidos."
    )
    bloque_obs = (
        f"\n\nOBSERVACIONES DEL JEFE DE ÁREA:\n{observaciones.strip()}"
        if observaciones.strip()
        else ""
    )

    prompt = f"""Eres un analista académico de la Carrera de Computación de la Universidad Politécnica Salesiana (UPS) Cuenca, Ecuador.

Revisas el aula virtual (AVAC) de la asignatura "{asignatura}", grupo {grupo}, a cargo del docente {docente}.

PARÁMETROS INCUMPLIDOS ({len(incumplidos)} de 12):
{detalle_incumplidos}{bloque_obs}

INSTRUCCIONES:
- Propón {min(max(len(incumplidos), 2), 4)} acciones de mejora concretas, cada una dirigida a subsanar un parámetro incumplido o a atender una observación.
- Formato: lista numerada, una oración por acción, en español formal e institucional.
- Sé específico: menciona el parámetro o recurso a corregir.
- No repitas el enunciado del parámetro; indica QUÉ debe hacer el docente.
- NO uses frases como "Es importante destacar" o "Es fundamental"."""

    return _llamar_ia(prompt, max_tokens=400)


def consolidar_avac_area(
    area: str,
    pct_cumplimiento: float,
    cumplidos: int,
    total: int,
    incumplidos_frecuentes: list[tuple[str, int]],
) -> dict:
    """Análisis del área y acciones generales, a partir de los parámetros que más fallan."""
    if total == 0:
        return {
            "analisis_area": "Checklists AVAC pendientes de completar.",
            "acciones_generales_avac": "",
        }

    tabla = "\n".join(
        f"- {PARAMETROS_AVAC.get(campo, campo)}: incumplido en {veces} asignatura(s)"
        for campo, veces in incumplidos_frecuentes
    ) or "- No hay parámetros incumplidos."

    analisis = _llamar_ia(
        f"""Eres un analista académico de la UPS Cuenca.

Área: {area}. Cumplimiento de los parámetros del aula virtual (AVAC): {pct_cumplimiento}%
({cumplidos} de {total} parámetros evaluados).

PARÁMETROS MÁS INCUMPLIDOS EN EL ÁREA:
{tabla}

Redacta 3-4 oraciones de análisis del cumplimiento del área. Menciona el porcentaje,
los parámetros que más fallan y qué implican para la calidad del aula virtual.
Español formal e institucional. No uses "Es importante destacar" ni "Es fundamental".""",
        max_tokens=400,
    )

    acciones = _llamar_ia(
        f"""Área: {area}. Cumplimiento AVAC: {pct_cumplimiento}%.

PARÁMETROS MÁS INCUMPLIDOS:
{tabla}

Propón 3-4 acciones de mejora generales para todo el equipo docente del área,
orientadas a corregir los parámetros que más fallan.
Lista numerada, una oración por acción. Español formal.""",
        max_tokens=400,
    )

    return {"analisis_area": analisis, "acciones_generales_avac": acciones}
