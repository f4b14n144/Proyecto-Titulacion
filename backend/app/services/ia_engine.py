"""
Motor de IA usando LiteLLM → claude-sonnet-4-20250514.

Genera análisis narrativos para los informes 3 y 4.
Todos los prompts están en español y producen texto listo para
pegar en el .docx institucional.

Manejo de errores: reintentos con backoff exponencial.
Si falla tras N intentos, devuelve texto de fallback genérico.
"""

import time
import statistics
from typing import Any
from loguru import logger
import litellm
from app.core.config import settings

litellm.set_verbose = False

MAX_REINTENTOS = 3
DELAY_BASE_SEG = 2.0  # espera exponencial: 2, 4, 8 seg


def _llamar_ia(prompt: str, max_tokens: int = 800) -> str:
    """
    Llama a LiteLLM con reintentos y backoff exponencial.
    Devuelve el texto generado o un mensaje de fallback.
    """
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "sk-ant-REEMPLAZAR":
        logger.warning("ANTHROPIC_API_KEY no configurada — devolviendo texto placeholder")
        return "[Análisis pendiente: configure ANTHROPIC_API_KEY en el archivo .env]"

    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            respuesta = litellm.completion(
                model=f"anthropic/{settings.AI_MODEL}",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                api_key=settings.ANTHROPIC_API_KEY,
            )
            texto = respuesta.choices[0].message.content.strip()
            logger.debug(f"IA respondió ({len(texto)} chars) en intento {intento}")
            return texto
        except Exception as e:
            logger.warning(f"Error IA intento {intento}/{MAX_REINTENTOS}: {e}")
            if intento < MAX_REINTENTOS:
                time.sleep(DELAY_BASE_SEG * (2 ** (intento - 1)))

    logger.error("IA falló tras todos los reintentos — usando fallback")
    return "[Análisis no disponible — error de conectividad con la IA. Editar manualmente.]"


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
