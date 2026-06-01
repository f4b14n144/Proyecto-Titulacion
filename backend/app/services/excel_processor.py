"""
Procesador de Excel de calificaciones UPS.

Maneja dos formatos:
  - INTERCICLO: columna de Parcial 1 (sobre 50 puntos)
  - FINAL: Parcial 1, Parcial 2, Recuperación, Nota Final, Estado

El Excel real de UPS tiene encabezados en filas superiores y los datos
de cada grupo separados por bloques. Este módulo los detecta automáticamente.
"""

import re
from typing import Any
import pandas as pd
from loguru import logger


# Sinónimos aceptados para cada columna (en minúsculas sin tildes)
_SINONIMOS: dict[str, list[str]] = {
    # Interciclo UPS: NOTA_APORTE_1 = Parcial 1; Finales UPS: "Primer Parcial"
    "parcial1":       ["parcial 1", "primer parcial", "p1", "nota parcial 1", "parcial1",
                       "nota aporte 1", "nota_aporte_1", "aporte 1", "aporte1"],
    "parcial2":       ["parcial 2", "segundo parcial", "p2", "nota parcial 2", "parcial2",
                       "nota aporte 2", "nota_aporte_2", "aporte 2", "aporte2"],
    "recuperacion":   ["recuperacion", "recuperación", "rec", "supletorio", "examen remedial"],
    # Finales UPS: "Nota Final"; Interciclo: "CALIFICACION_FINAL"
    "nota_final":     ["nota final", "calificacion final", "calificación final", "promedio final",
                       "nota_final", "calificacion_final"],
    # Finales UPS: "Estado de la Materia"; Interciclo: "ESTADO"
    "estado":         ["estado", "condicion", "condición", "resultado", "aprobado/reprobado",
                       "estado de la materia", "estado_materia"],
    "docente":        ["docente", "profesor", "teacher", "nombre docente"],
    "asignatura":     ["asignatura", "materia", "subject", "nombre asignatura"],
    "grupo":          ["grupo", "paralelo", "group", "seccion", "sección"],
}


def _normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, sin caracteres especiales."""
    t = str(texto).lower().strip()
    for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9 _]", "", t)


def _detectar_columna(encabezados: list[str], campo: str) -> str | None:
    """
    Devuelve el encabezado original que corresponde a un campo lógico.
    Prioriza coincidencias exactas sobre substrings para evitar que
    "CODIGO_GRUPO" se elija antes que "GRUPO".
    """
    sinonimos = _SINONIMOS.get(campo, [])
    # Primera pasada: coincidencia exacta
    for enc in encabezados:
        norm = _normalizar(enc)
        if norm in sinonimos:
            return enc
    # Segunda pasada: el nombre normalizado contiene algún sinónimo
    # pero excluir columnas que empiezan con prefijos indicadores de otro campo
    PREFIJOS_EXCLUIR = {"codigo", "num", "numero", "id"}
    for enc in encabezados:
        norm = _normalizar(enc)
        primera_palabra = norm.split("_")[0].split(" ")[0]
        if primera_palabra in PREFIJOS_EXCLUIR:
            continue
        if any(s in norm for s in sinonimos):
            return enc
    return None


def _limpiar_nota(valor: Any) -> float | None:
    """Convierte un valor de celda a float, devuelve None si no es numérico."""
    if pd.isna(valor):
        return None
    try:
        return float(str(valor).replace(",", ".").strip())
    except ValueError:
        return None


def _detectar_inicio_datos(df: pd.DataFrame) -> int:
    """
    Busca la fila donde empiezan los datos (la fila con los nombres de columnas).
    Los Excels UPS de calificaciones finales tienen 10 filas de encabezado institucional.
    Estrategia: buscar la primera fila con >= 5 celdas no-vacías con texto alfanumérico.
    """
    for i, row in df.iterrows():
        valores = [str(v).strip() for v in row.values if str(v).strip() and str(v) != 'nan']
        if len(valores) >= 5:
            return int(str(i))
    return 0


def _extraer_numero_grupo(grupo_raw: str) -> str:
    """
    Extrae el número de grupo del formato UPS: "GRUPO - 1 - COMPUTACIÓN - CUE" → "G1".
    Si no puede extraer, devuelve el valor limpio.
    """
    m = re.search(r'GRUPO\s*-\s*(\d+)', str(grupo_raw), re.IGNORECASE)
    if m:
        return f"G{m.group(1)}"
    return str(grupo_raw).strip()


def procesar_excel(
    ruta_archivo: str,
    tipo: str,  # INTERCICLO | FINAL
    asignaciones_periodo: list[dict],
    # [{"asignatura_id": int, "asignatura_nombre": str, "asignatura_codigo": str,
    #   "usuario_id": int, "grupo": str}]
) -> list[dict]:
    """
    Lee el Excel y retorna una lista de resultados por asignatura+grupo:

    [
      {
        "asignatura_id": int,
        "grupo": str,
        "estudiantes": [{"parcial1": N, "parcial2": N, "recuperacion": N,
                         "nota_final": N, "estado": str}],
        "total_estudiantes": int,
        "columnas_detectadas": [str],
        "advertencias": [str],
      }
    ]
    """
    logger.info(f"Procesando Excel tipo={tipo}: {ruta_archivo}")
    advertencias_globales: list[str] = []

    try:
        # Leer sin asumir encabezados — explorar primero
        df_raw = pd.read_excel(ruta_archivo, header=None, dtype=str)
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo Excel: {e}")

    # Detectar fila de encabezados
    fila_enc = _detectar_inicio_datos(df_raw)
    df = pd.read_excel(ruta_archivo, header=fila_enc, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]

    logger.debug(f"Columnas detectadas en Excel: {list(df.columns)}")

    # Mapear columnas lógicas → columnas reales del Excel
    col_map: dict[str, str | None] = {
        "parcial1":     _detectar_columna(list(df.columns), "parcial1"),
        "parcial2":     _detectar_columna(list(df.columns), "parcial2"),
        "recuperacion": _detectar_columna(list(df.columns), "recuperacion"),
        "nota_final":   _detectar_columna(list(df.columns), "nota_final"),
        "estado":       _detectar_columna(list(df.columns), "estado"),
        "asignatura":   _detectar_columna(list(df.columns), "asignatura"),
        "grupo":        _detectar_columna(list(df.columns), "grupo"),
    }

    columnas_presentes = [k for k, v in col_map.items() if v is not None]
    logger.info(f"Columnas mapeadas: {columnas_presentes}")

    # Validaciones mínimas según tipo
    if tipo == "INTERCICLO" and col_map["parcial1"] is None:
        raise ValueError(
            "Excel INTERCICLO: no se encontró columna de Parcial 1. "
            f"Columnas disponibles: {list(df.columns)}"
        )
    if tipo == "FINAL" and col_map["nota_final"] is None:
        raise ValueError(
            "Excel FINAL: no se encontró columna de Nota Final. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    # Eliminar filas completamente vacías
    df = df.dropna(how="all")

    resultados: list[dict] = []

    # Estrategia: agrupar por asignatura+grupo si las columnas existen en el Excel,
    # o bien procesar el archivo completo y cruzar con las asignaciones del período.
    if col_map["asignatura"] and col_map["grupo"]:
        grupos = df.groupby([col_map["asignatura"], col_map["grupo"]])  # type: ignore[index]
        for (nombre_asig, grupo_val), bloque in grupos:
            # Normalizar el número de grupo (UPS: "GRUPO - 1 - COMPUTACIÓN - CUE" → "G1")
            grupo_norm = _extraer_numero_grupo(str(grupo_val))
            asig_match = _buscar_asignacion(
                str(nombre_asig), grupo_norm, asignaciones_periodo
            )
            if asig_match is None:
                advertencias_globales.append(
                    f"Sin asignación registrada: '{nombre_asig}' grupo '{grupo_norm}'"
                )
                continue
            estudiantes, adv = _extraer_estudiantes(bloque, col_map, tipo)
            resultados.append(_construir_resultado(asig_match, grupo_norm, estudiantes, columnas_presentes, adv))
    else:
        # El Excel no tiene columnas de asignatura/grupo → una sola asignatura
        if len(asignaciones_periodo) == 1:
            asig = asignaciones_periodo[0]
            estudiantes, adv = _extraer_estudiantes(df, col_map, tipo)
            resultados.append(_construir_resultado(asig, asig["grupo"], estudiantes, columnas_presentes, adv))
        else:
            advertencias_globales.append(
                "El Excel no contiene columnas de asignatura/grupo pero hay múltiples "
                "asignaciones en el período. No se puede asignar automáticamente."
            )

    if advertencias_globales:
        logger.warning(f"Advertencias al procesar Excel: {advertencias_globales}")

    return resultados


def _buscar_asignacion(nombre_asig: str, grupo: str, asignaciones: list[dict]) -> dict | None:
    """Busca la asignación que coincide por nombre/código y grupo (fuzzy tolerante)."""
    norm_asig = _normalizar(nombre_asig)
    norm_grupo = _normalizar(grupo)
    for a in asignaciones:
        cond_asig = (
            _normalizar(a.get("asignatura_nombre", "")) in norm_asig
            or norm_asig in _normalizar(a.get("asignatura_nombre", ""))
            or _normalizar(a.get("asignatura_codigo", "")) in norm_asig
        )
        cond_grupo = _normalizar(a.get("grupo", "")) == norm_grupo
        if cond_asig and cond_grupo:
            return a
    # Segunda pasada: solo por código
    for a in asignaciones:
        if _normalizar(a.get("asignatura_codigo", "")) in norm_asig:
            return a
    return None


def _extraer_estudiantes(
    df: pd.DataFrame,
    col_map: dict[str, str | None],
    tipo: str,
) -> tuple[list[dict], list[str]]:
    """Extrae la lista de estudiantes de un bloque del DataFrame."""
    estudiantes: list[dict] = []
    advertencias: list[str] = []

    for _, row in df.iterrows():
        p1 = _limpiar_nota(row.get(col_map["parcial1"]) if col_map["parcial1"] else None)
        p2 = _limpiar_nota(row.get(col_map["parcial2"]) if col_map["parcial2"] else None)
        rec = _limpiar_nota(row.get(col_map["recuperacion"]) if col_map["recuperacion"] else None)
        nf = _limpiar_nota(row.get(col_map["nota_final"]) if col_map["nota_final"] else None)

        # Saltar filas sin ninguna nota
        if all(v is None for v in [p1, p2, rec, nf]):
            continue

        # Determinar estado
        estado_raw = str(row.get(col_map["estado"]) if col_map["estado"] else "").strip().upper()
        if estado_raw in ("APROBADO", "REPROBADO", "APROBADA", "REPROBADA"):
            estado = "APROBADO" if "APROBAD" in estado_raw else "REPROBADO"
        elif nf is not None:
            estado = "APROBADO" if nf >= 14.0 else "REPROBADO"
        elif p1 is not None and tipo == "INTERCICLO":
            estado = "APROBADO" if p1 >= 25.0 else "BAJO"  # sobre 50
        else:
            estado = "DESCONOCIDO"

        est: dict[str, Any] = {
            "parcial1":     p1,
            "parcial2":     p2,
            "recuperacion": rec,
            "nota_final":   nf,
            "estado":       estado,
        }

        # Caso especial: parciales en 0 y solo hay nota final
        if p1 == 0.0 and p2 == 0.0 and nf is not None and nf > 0:
            advertencias.append("Estudiante con parciales en 0 y nota final > 0 (solo nota final disponible)")
            est["solo_nota_final"] = True

        estudiantes.append(est)

    return estudiantes, advertencias


def _construir_resultado(
    asignacion: dict,
    grupo: str,
    estudiantes: list[dict],
    columnas_detectadas: list[str],
    advertencias: list[str],
) -> dict:
    return {
        "asignatura_id":       asignacion["asignatura_id"],
        "grupo":               grupo,
        "estudiantes":         estudiantes,
        "total_estudiantes":   len(estudiantes),
        "columnas_detectadas": columnas_detectadas,
        "advertencias":        advertencias,
    }
