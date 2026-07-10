"""
Gráficos para los informes.

Se generan como PNG y se incrustan en el .docx (y se sirven al panel en base64).

Decisiones de diseño:
- Los rangos ALTO / MEDIO / BAJO son **categorías ordenadas** (bandas de
  desempeño), no identidades independientes. Por eso usan una **rampa ordinal de
  un solo tono** (azul, claro→oscuro) en lugar de tres colores distintos: el color
  codifica el orden y no inventa una diferencia de identidad.
- Un pastel de dos rebanadas no aporta nada sobre el número; solo se dibuja
  cuando hay al menos dos rangos con datos.
- Sin sombras, sin explosionar rebanadas, sin bordes de separación: se usa una
  separación de 2 px del color de la superficie entre porciones.
"""
import base64
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # sin display: el backend corre headless
import matplotlib.pyplot as plt  # noqa: E402

# Rampa ordinal de un solo tono (azul), claro→oscuro.
# Validada: lightness monótona, ΔL suficiente, el paso más claro contrasta 2.11:1
# contra la hoja blanca del documento.
_RAMPA = {
    "bajo": "#86b6ef",
    "medio": "#3987e5",
    "alto": "#184f95",
}
_SUPERFICIE = "#ffffff"
_TINTA = "#333333"
_TINTA_TENUE = "#6b6b6b"


def _hay_datos(stats: dict) -> bool:
    total = (stats.get("rango_alto", 0) or 0) + (stats.get("rango_medio", 0) or 0) \
        + (stats.get("rango_bajo", 0) or 0)
    return total > 0


def grafico_rangos_interciclo(stats: dict, titulo: str = "") -> bytes | None:
    """
    Pastel de la distribución por rango de desempeño del primer parcial.

    Devuelve los bytes del PNG, o None si no hay datos suficientes.
    """
    if not _hay_datos(stats):
        return None

    segmentos = [
        ("Rango alto (≥40/50)", stats.get("rango_alto", 0) or 0, _RAMPA["alto"]),
        ("Rango medio (30–39/50)", stats.get("rango_medio", 0) or 0, _RAMPA["medio"]),
        ("Rango bajo (<30/50)", stats.get("rango_bajo", 0) or 0, _RAMPA["bajo"]),
    ]
    # Solo las porciones con estudiantes; un pastel de una sola rebanada no dice nada
    segmentos = [s for s in segmentos if s[1] > 0]
    if len(segmentos) < 2:
        return None

    etiquetas = [s[0] for s in segmentos]
    valores = [s[1] for s in segmentos]
    colores = [s[2] for s in segmentos]
    total = sum(valores)

    fig, ax = plt.subplots(figsize=(5.6, 3.4), dpi=200)
    fig.patch.set_facecolor(_SUPERFICIE)
    ax.set_facecolor(_SUPERFICIE)

    porciones, _, autotextos = ax.pie(
        valores,
        colors=colores,
        startangle=90,
        counterclock=False,
        autopct=lambda p: f"{p:.0f}%" if p >= 6 else "",  # no etiquetar lo ilegible
        pctdistance=0.62,
        # Separación de 2px del color de la superficie entre porciones
        wedgeprops={"linewidth": 2, "edgecolor": _SUPERFICIE},
        textprops={"fontsize": 9},
    )

    # El porcentaje se lee sobre el color: blanco en los pasos oscuros
    for texto, color in zip(autotextos, colores):
        texto.set_color(_SUPERFICIE if color != _RAMPA["bajo"] else _TINTA)
        texto.set_fontweight("bold")

    ax.axis("equal")

    # La identidad nunca depende solo del color: leyenda con el conteo
    ax.legend(
        porciones,
        [f"{e} — {v} ({v / total * 100:.0f}%)" for e, v in zip(etiquetas, valores)],
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        frameon=False,
        fontsize=8.5,
        labelcolor=_TINTA,
    )

    if titulo:
        ax.set_title(titulo, fontsize=10, color=_TINTA, pad=10)
    fig.text(
        0.01, 0.02, f"{total} estudiantes evaluados",
        fontsize=7.5, color=_TINTA_TENUE,
    )

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", facecolor=_SUPERFICIE)
    plt.close(fig)
    return buffer.getvalue()


def guardar_png(datos: bytes, ruta: Path) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(datos)
    return ruta


def a_data_uri(datos: bytes) -> str:
    """PNG en base64 para mostrarlo directamente en el panel."""
    return "data:image/png;base64," + base64.b64encode(datos).decode("ascii")
