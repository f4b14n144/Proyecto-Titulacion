"""
Procesador del Excel de estudiantes por período.

El archivo institucional trae, en columnas cuyo orden y nombre no están
garantizados: el **nombre** del estudiante, su **correo institucional** y las
**materias que cursa**. Este módulo las reconoce sin depender de la posición.

Estrategia de detección, en tres capas (de más fiable a menos):
  1. **Por contenido**: la columna de correo se detecta por el propio dato
     (regex de email). No depende del encabezado.
  2. **Por encabezado**: sinónimos normalizados (sin tildes, minúsculas).
  3. **Con IA**: si algo sigue sin identificarse, se le pasan los encabezados y
     unas filas de muestra al modelo para que devuelva el mapeo en JSON.
"""
import json
import re
from typing import Any

import pandas as pd
from loguru import logger

from app.services.excel_processor import _detectar_inicio_datos, _normalizar

# Un correo institucional real basta para identificar la columna
_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")

# Separadores posibles cuando varias materias van en una sola celda
_SEPARADORES = re.compile(r"[;|\n/]+")

_SINONIMOS: dict[str, list[str]] = {
    "nombre": [
        "nombre", "nombres", "nombre completo", "nombre del estudiante",
        "estudiante", "alumno", "apellidos y nombres", "nombres y apellidos",
    ],
    "apellido": ["apellido", "apellidos", "apellido paterno", "apellidos del estudiante"],
    "correo": [
        "correo", "correos", "email", "e mail", "mail", "correo institucional",
        "correo electronico", "email institucional",
    ],
    "materias": [
        "materia", "materias", "asignatura", "asignaturas",
        "materias cursando", "materias que cursa", "nombre de la materia",
        "asignaturas cursando",
    ],
}


# ──────────────────────────────────────────────────────────────────
# Detección de columnas
# ──────────────────────────────────────────────────────────────────

def _columna_de_correo_por_contenido(df: pd.DataFrame) -> str | None:
    """La columna donde la mayoría de los valores parecen un email."""
    mejor, mejor_ratio = None, 0.0
    for col in df.columns:
        valores = df[col].dropna().astype(str).str.strip()
        if valores.empty:
            continue
        ratio = valores.apply(lambda v: bool(_RE_EMAIL.match(v))).mean()
        if ratio > mejor_ratio:
            mejor, mejor_ratio = col, float(ratio)
    return mejor if mejor_ratio >= 0.7 else None


def _columna_de_materias_por_contenido(
    df: pd.DataFrame, catalogo: list[dict], excluir: set[str]
) -> str | None:
    """
    La columna cuyos valores coinciden con asignaturas del catálogo de la carrera.

    Es una señal muy fuerte: no depende del encabezado ni del idioma.
    """
    if not catalogo:
        return None
    normalizadas = {_normalizar(a["nombre"]) for a in catalogo if a.get("nombre")}

    def _coincide(celda: str) -> bool:
        for parte in _separar_materias(celda):
            n = _normalizar(parte)
            if not n:
                continue
            if n in normalizadas or any(n in c or c in n for c in normalizadas):
                return True
        return False

    mejor, mejor_ratio = None, 0.0
    for col in df.columns:
        if col in excluir:
            continue
        valores = df[col].dropna().astype(str)
        if valores.empty:
            continue
        ratio = float(valores.apply(_coincide).mean())
        if ratio > mejor_ratio:
            mejor, mejor_ratio = col, ratio
    return mejor if mejor_ratio >= 0.5 else None


def _columna_de_nombre_por_contenido(df: pd.DataFrame, excluir: set[str]) -> str | None:
    """La columna con nombres de persona: varias palabras, solo letras, sin dígitos ni @."""
    def _parece_nombre(v: str) -> bool:
        v = v.strip()
        if not v or "@" in v or any(ch.isdigit() for ch in v):
            return False
        palabras = v.split()
        return len(palabras) >= 2 and all(p.replace("-", "").isalpha() for p in palabras)

    mejor, mejor_ratio = None, 0.0
    for col in df.columns:
        if col in excluir:
            continue
        valores = df[col].dropna().astype(str)
        if valores.empty:
            continue
        ratio = float(valores.apply(_parece_nombre).mean())
        if ratio > mejor_ratio:
            mejor, mejor_ratio = col, ratio
    return mejor if mejor_ratio >= 0.7 else None


def _columna_por_encabezado(encabezados: list[str], campo: str) -> str | None:
    sinonimos = _SINONIMOS[campo]
    # Coincidencia exacta primero
    for enc in encabezados:
        if _normalizar(enc) in sinonimos:
            return enc
    # Luego, que el encabezado contenga algún sinónimo
    for enc in encabezados:
        norm = _normalizar(enc)
        if any(s in norm for s in sinonimos):
            return enc
    return None


def _detectar_columnas_con_ia(df: pd.DataFrame) -> dict[str, str | None]:
    """
    Último recurso: le pide al modelo que identifique las columnas.

    Se le dan los encabezados y 3 filas de muestra; debe devolver JSON con los
    nombres EXACTOS de columna (o null si no existe).
    """
    from app.services.ia_engine import _llamar_ia

    encabezados = [str(c) for c in df.columns]
    muestra = df.head(3).astype(str).to_dict(orient="records")

    prompt = (
        "Eres un asistente que identifica columnas de una hoja de cálculo de estudiantes "
        "universitarios.\n\n"
        f"Encabezados: {json.dumps(encabezados, ensure_ascii=False)}\n"
        f"Filas de muestra: {json.dumps(muestra, ensure_ascii=False)}\n\n"
        "Devuelve ÚNICAMENTE un objeto JSON, sin explicaciones ni markdown, con estas claves:\n"
        '{"nombre": <encabezado del nombre del estudiante o null>,\n'
        ' "apellido": <encabezado del apellido si va en columna aparte, o null>,\n'
        ' "correo": <encabezado del correo institucional o null>,\n'
        ' "materias": <encabezado de las materias que cursa o null>}\n\n'
        "Usa los encabezados EXACTAMENTE como aparecen en la lista."
    )

    try:
        respuesta = _llamar_ia(prompt, max_tokens=300)
        texto = respuesta.strip()
        # El modelo a veces envuelve el JSON en ```json ... ```
        m = re.search(r"\{.*\}", texto, re.S)
        if not m:
            logger.warning(f"La IA no devolvió JSON al detectar columnas: {texto[:120]}")
            return {}
        datos = json.loads(m.group(0))
    except Exception as e:  # noqa: BLE001 — nunca debe tumbar la carga
        logger.warning(f"Falló la detección de columnas con IA: {e}")
        return {}

    # Solo aceptamos encabezados que existan de verdad
    validos = {}
    for campo in ("nombre", "apellido", "correo", "materias"):
        valor = datos.get(campo)
        if isinstance(valor, str) and valor in encabezados:
            validos[campo] = valor
    logger.info(f"IA detectó columnas: {validos}")
    return validos


def detectar_columnas(
    df: pd.DataFrame, catalogo: list[dict] | None = None
) -> tuple[dict[str, str | None], list[str]]:
    """
    Devuelve el mapeo campo → encabezado real, y cómo se detectó cada uno.

    Orden: contenido (correo) → encabezado → contenido (materias, nombre) → IA.
    El encabezado va antes que el contenido para nombre/apellido, porque cuando
    vienen separados solo el encabezado distingue cuál es cuál.
    """
    catalogo = catalogo or []
    encabezados = [str(c) for c in df.columns]
    col: dict[str, str | None] = {"nombre": None, "apellido": None, "correo": None, "materias": None}
    notas: list[str] = []

    # 1. El correo, por su contenido (no depende del encabezado)
    col["correo"] = _columna_de_correo_por_contenido(df)
    if col["correo"]:
        notas.append(f"Correo detectado por contenido: '{col['correo']}'")

    # 2. Por encabezado
    for campo in ("nombre", "apellido", "materias", "correo"):
        if col[campo] is None:
            encontrado = _columna_por_encabezado(encabezados, campo)
            if encontrado:
                col[campo] = encontrado
                notas.append(f"{campo.capitalize()} detectado por encabezado: '{encontrado}'")

    usadas = {v for v in col.values() if v}

    # 3. Por contenido: las materias se reconocen contra el catálogo de la carrera
    if col["materias"] is None:
        encontrado = _columna_de_materias_por_contenido(df, catalogo, usadas)
        if encontrado:
            col["materias"] = encontrado
            usadas.add(encontrado)
            notas.append(f"Materias detectadas por contenido (catálogo): '{encontrado}'")

    # 4. Por contenido: el nombre es la columna con nombres de persona
    if col["nombre"] is None:
        encontrado = _columna_de_nombre_por_contenido(df, usadas)
        if encontrado:
            col["nombre"] = encontrado
            usadas.add(encontrado)
            notas.append(f"Nombre detectado por contenido: '{encontrado}'")

    # 5. Lo que aún falte, con IA
    faltan = [c for c in ("nombre", "correo", "materias") if col[c] is None]
    if faltan:
        notas.append(f"Sin identificar por heurística: {', '.join(faltan)}. Consultando a la IA…")
        sugerido = _detectar_columnas_con_ia(df)
        for campo, enc in sugerido.items():
            if col.get(campo) is None:
                col[campo] = enc
                notas.append(f"{campo.capitalize()} detectado por IA: '{enc}'")

    return col, notas


# ──────────────────────────────────────────────────────────────────
# Extracción
# ──────────────────────────────────────────────────────────────────

def _separar_materias(celda: Any) -> list[str]:
    """Una celda puede traer una materia o varias separadas por ; | / o coma."""
    if pd.isna(celda):
        return []
    texto = str(celda).strip()
    if not texto:
        return []
    partes = [p.strip() for p in _SEPARADORES.split(texto) if p.strip()]
    # Si no había separador fuerte pero sí comas, se usan las comas
    if len(partes) == 1 and "," in partes[0]:
        partes = [p.strip() for p in partes[0].split(",") if p.strip()]
    return partes


def _resolver_asignatura(nombre: str, catalogo: list[dict]) -> int | None:
    """Empareja el nombre de la materia con el catálogo de la carrera."""
    norm = _normalizar(nombre)
    if not norm:
        return None
    for a in catalogo:
        if _normalizar(a["nombre"]) == norm:
            return a["id"]
    for a in catalogo:
        cat = _normalizar(a["nombre"])
        if cat and (cat in norm or norm in cat):
            return a["id"]
    return None


def procesar_excel_estudiantes(
    ruta_archivo: str,
    catalogo_asignaturas: list[dict],  # [{"id": int, "nombre": str}]
) -> dict:
    """
    Lee el Excel y agrupa por estudiante (identificado por su correo).

    Soporta los dos formatos habituales:
      - una fila por (estudiante, materia)
      - una fila por estudiante con todas sus materias en una celda
    """
    try:
        crudo = pd.read_excel(ruta_archivo, header=None, dtype=str)
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo Excel: {e}")

    fila_enc = _detectar_inicio_datos(crudo)
    df = pd.read_excel(ruta_archivo, header=fila_enc, dtype=str).dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]

    col, notas = detectar_columnas(df, catalogo_asignaturas)
    advertencias = list(notas)

    faltantes = [c for c in ("nombre", "correo", "materias") if col[c] is None]
    if faltantes:
        raise ValueError(
            "No se pudieron identificar estas columnas en el Excel: "
            f"{', '.join(faltantes)}. Columnas disponibles: {list(df.columns)}"
        )

    estudiantes: dict[str, dict] = {}
    sin_correo = 0

    for _, fila in df.iterrows():
        correo = str(fila.get(col["correo"]) or "").strip()
        if not _RE_EMAIL.match(correo):
            sin_correo += 1
            continue

        nombre = str(fila.get(col["nombre"]) or "").strip()
        if col["apellido"]:
            apellido = str(fila.get(col["apellido"]) or "").strip()
            nombre = f"{apellido} {nombre}".strip() if apellido else nombre
        if not nombre:
            nombre = correo.split("@")[0]

        est = estudiantes.setdefault(
            correo.lower(), {"nombre_completo": nombre, "correo": correo.lower(), "materias": []}
        )

        for materia in _separar_materias(fila.get(col["materias"])):
            if any(m["asignatura_nombre"].lower() == materia.lower() for m in est["materias"]):
                continue
            est["materias"].append({
                "asignatura_nombre": materia,
                "asignatura_id": _resolver_asignatura(materia, catalogo_asignaturas),
            })

    lista = list(estudiantes.values())
    total_materias = sum(len(e["materias"]) for e in lista)
    sin_catalogo = sum(
        1 for e in lista for m in e["materias"] if m["asignatura_id"] is None
    )

    if sin_correo:
        advertencias.append(f"Se omitieron {sin_correo} fila(s) sin un correo válido.")
    if sin_catalogo:
        advertencias.append(
            f"{sin_catalogo} materia(s) no coinciden con el catálogo de la carrera; "
            "se conservará el nombre tal como vino en el Excel."
        )

    logger.info(
        f"Excel de estudiantes: {len(lista)} estudiantes, {total_materias} materias, "
        f"columnas={col}"
    )

    return {
        "columnas_detectadas": col,
        "estudiantes": lista,
        "total_estudiantes": len(lista),
        "total_materias": total_materias,
        "advertencias": advertencias,
    }
