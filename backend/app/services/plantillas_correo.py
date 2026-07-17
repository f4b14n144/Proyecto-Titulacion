"""
Plantillas de los correos institucionales.

El texto es el entregado por la dirección de carrera y no debe alterarse: solo se
sustituyen los datos personalizados (docente, estudiante, materia, remitente).

Cada función devuelve `(asunto, cuerpo_html)`. El logo de la universidad va en el
**pie institucional**, junto a la firma; se referencia por Content-ID y lo adjunta
`mail_service.enviar_email` como imagen inline.
"""
from html import escape

_TEXTO = "line-height:1.5;font-family:Calibri,Arial,sans-serif;font-size:14px;color:#333"
_ESTILO_P = f'style="margin:0 0 12px 0;{_TEXTO}"'
_ESTILO_UL = f'style="margin:0 0 12px 20px;{_TEXTO}"'

UNIVERSIDAD = "Universidad Politécnica Salesiana"
CARRERA = "Carrera de Ciencias de la Computación"


def _p(texto: str) -> str:
    return f"<p {_ESTILO_P}>{texto}</p>"


def _lista(items: list[str]) -> str:
    lis = "".join(f"<li>{i}</li>" for i in items)
    return f"<ul {_ESTILO_UL}>{lis}</ul>"


def _tratamiento(titulo_docente: str) -> str:
    """
    "Estimado/a [titulo]. [Nombre]" — el título ya suele traer su punto ("Ing."),
    así que se normaliza para no terminar con "Ing.." ni pegado al nombre.
    """
    titulo = (titulo_docente or "").strip().rstrip(".").strip()
    return f"{escape(titulo)}. " if titulo else ""


def _firma(remitente_nombre: str, remitente_cargo: str) -> str:
    """
    Pie institucional: la firma a la izquierda y el logo de la universidad a la
    derecha, separados del cuerpo por una línea.

    Se usa una tabla porque es la única forma fiable de alinear dos bloques en
    los clientes de correo (Outlook no soporta flexbox). El logo se referencia
    por Content-ID; lo adjunta `mail_service.enviar_email`.
    """
    firma_texto = (
        f"<strong>{escape(remitente_nombre)}</strong><br>"
        f"{escape(remitente_cargo)}<br>"
        f"{CARRERA}<br>"
        f"{UNIVERSIDAD}"
    )
    return (
        _p("Atentamente,")
        + f"""
        <table role="presentation" cellpadding="0" cellspacing="0" border="0"
               style="width:100%;max-width:620px;margin-top:14px;border-top:1px solid #d9d9d9">
          <tr>
            <td style="padding-top:12px;vertical-align:middle;{_TEXTO}">
              {firma_texto}
            </td>
            <td style="padding-top:12px;vertical-align:middle;text-align:right;width:190px">
              <img src="cid:logo_ups" alt="{UNIVERSIDAD}"
                   style="height:52px;display:block;margin-left:auto">
            </td>
          </tr>
        </table>
        """
    )


# ──────────────────────────────────────────────────────────────────
# Anexo B — Correo a DOCENTES (observaciones y acciones de mejora)
# ──────────────────────────────────────────────────────────────────

def correo_docente_materia(
    titulo_docente: str,
    nombre_docente: str,
    nombre_materia: str,
    remitente_nombre: str,
    remitente_cargo: str,
) -> tuple[str, str]:
    tratamiento = _tratamiento(titulo_docente)
    asunto = f"Solicitud de observaciones y propuestas de mejora — {nombre_materia}"

    cuerpo = (
        _p(f"Estimado/a {tratamiento}{escape(nombre_docente)}:")
        + _p("Reciba un cordial saludo.")
        + _p(
            "Con el objetivo de fortalecer los procesos de evaluación y mejora continua de la "
            f"{CARRERA}, me permito solicitar muy comedidamente su valiosa colaboración mediante "
            "el envío de observaciones y propuestas de mejora relacionadas con la asignatura "
            f'"<strong>{escape(nombre_materia)}</strong>", que actualmente imparte.'
        )
        + _p("En caso de considerarlo pertinente, agradeceré remitir la siguiente información:")
        + _lista([
            "<strong>Observaciones del Docente a la Materia</strong>, en las que pueda exponer "
            "los aspectos relevantes identificados durante el desarrollo de la asignatura.",
            "<strong>Acciones de Mejora propuestas por el Docente a la Materia</strong>, en las "
            "que plantee recomendaciones o iniciativas orientadas al fortalecimiento del proceso "
            "de enseñanza-aprendizaje y a la mejora continua de la asignatura.",
        ])
        + _p(
            "Su aporte constituye un insumo de gran valor para el análisis, la evaluación y el "
            "fortalecimiento continuo de la carrera, por lo que agradezco de antemano su tiempo, "
            "disposición y colaboración."
        )
        + _p("Quedo atento/a a cualquier consulta o información adicional que requiera.")
        + _firma(remitente_nombre, remitente_cargo)
    )
    return asunto, cuerpo


# ──────────────────────────────────────────────────────────────────
# Anexo C — Correo a ESTUDIANTES (apreciaciones sobre la asignatura)
# ──────────────────────────────────────────────────────────────────

def correo_estudiante_materia(
    nombre_estudiante: str,
    nombre_materia: str,
    titulo_docente: str,
    nombre_docente: str,
    remitente_nombre: str,
    remitente_cargo: str,
) -> tuple[str, str]:
    docente = f"{titulo_docente} {nombre_docente}".strip()
    asunto = f"Consulta sobre el desarrollo de la asignatura — {nombre_materia}"

    cuerpo = (
        _p(f"Estimado/a {escape(nombre_estudiante)}:")
        + _p("Reciba un cordial saludo.")
        + _p(
            "Como parte de los procesos de seguimiento académico y mejora continua de la "
            f"{CARRERA}, me permito solicitar muy comedidamente su colaboración para conocer sus "
            "apreciaciones respecto al desarrollo de la asignatura "
            f'"<strong>{escape(nombre_materia)}</strong>", impartida por el/la '
            f"<strong>{escape(docente)}</strong>."
        )
        + _p(
            "En caso de que lo considere pertinente, agradeceré que pueda compartir observaciones "
            "relacionadas con alguno de los siguientes aspectos:"
        )
        + _lista([
            "La asistencia y puntualidad del docente.",
            "El cumplimiento del contenido establecido en el sílabo de la asignatura.",
            "La realización de prácticas, cuando estas correspondan a la naturaleza de la materia.",
            "La utilización de rúbricas para las actividades calificadas (evaluaciones, trabajos, "
            "foros, proyectos u otras).",
            "La realización de actividades que fomenten la participación de los estudiantes en "
            "procesos de investigación.",
            "Cualquier otra observación o sugerencia que considere importante respecto al "
            "desarrollo de la asignatura o al proceso de enseñanza-aprendizaje.",
        ])
        + _p(
            "Es importante señalar que, si considera que el desarrollo de la asignatura se está "
            "llevando a cabo de manera adecuada y no tiene observaciones que realizar, no es "
            "necesario responder a este correo. La respuesta únicamente será necesaria si desea "
            "comunicar alguna observación, comentario o sugerencia que contribuya al "
            "fortalecimiento de la calidad académica."
        )
        + _p(
            "Toda la información recibida será tratada con la debida reserva y utilizada "
            "exclusivamente con fines de seguimiento académico y de mejora continua."
        )
        + _p(
            "Agradezco de antemano su tiempo, colaboración y compromiso con el fortalecimiento "
            "de nuestra carrera."
        )
        + _firma(remitente_nombre, remitente_cargo)
    )
    return asunto, cuerpo


# ──────────────────────────────────────────────────────────────────
# Correo a DOCENTES sobre visitas áulicas (requerimiento 14)
# ──────────────────────────────────────────────────────────────────

def correo_visita_aulica(
    titulo_docente: str,
    nombre_docente: str,
    nombre_materia: str,
    remitente_nombre: str,
    remitente_cargo: str,
) -> tuple[str, str]:
    tratamiento = _tratamiento(titulo_docente)
    asunto = f"Visita áulica — {nombre_materia}"

    cuerpo = (
        _p(f"Estimado/a {tratamiento}{escape(nombre_docente)}:")
        + _p("Reciba un cordial saludo.")
        + _p(
            "Dentro del proceso de acompañamiento y mejora continua de la "
            f"{CARRERA}, se ha previsto realizar una <strong>visita áulica</strong> a la "
            f'asignatura "<strong>{escape(nombre_materia)}</strong>", que usted imparte.'
        )
        + _p(
            "Con el fin de coordinar la visita y contar con la información necesaria, agradeceré "
            "que pueda confirmarnos los siguientes aspectos:"
        )
        + _lista([
            "Día y hora más convenientes para realizar la visita.",
            "El avance del sílabo y el contenido previsto para esa sesión.",
            "Si la sesión contempla componente práctico o de laboratorio.",
            "Las rúbricas utilizadas para las actividades calificadas.",
            "Las actividades orientadas a fomentar la participación de los estudiantes en "
            "procesos de investigación.",
        ])
        + _p(
            "La visita tiene un carácter formativo y de acompañamiento; su propósito es "
            "identificar buenas prácticas y oportunidades de mejora, nunca fiscalizar."
        )
        + _p("Quedo atento/a a su respuesta y agradezco de antemano su colaboración.")
        + _firma(remitente_nombre, remitente_cargo)
    )
    return asunto, cuerpo


# ──────────────────────────────────────────────────────────────────
# Recordatorios automáticos (los envía el planificador, 2 días antes)
# ──────────────────────────────────────────────────────────────────

NOMBRE_INFORME = {
    1: "Informe 1 — Centro Docente",
    2: "Informe 2 — Revisión del Aula Virtual (AVAC)",
    3: "Informe 3 — Visitas Áulicas e Interciclo",
    4: "Informe 4 — Análisis Final de Calificaciones",
}

# Qué le toca hacer a cada rol en cada informe
_TAREAS_JEFE = {
    1: ["Añadir el aporte de su área a las secciones del Consejo de Carrera."],
    2: [
        "Completar el checklist de los 12 parámetros del aula virtual (AVAC) de cada "
        "asignatura de su área.",
        "Registrar sus observaciones y acciones de mejora.",
    ],
    3: [
        "Registrar el checklist de las visitas áulicas realizadas.",
        "Revisar el análisis de las calificaciones de interciclo.",
    ],
    4: ["Revisar el análisis final de calificaciones y las acciones de mejora del área."],
}


def correo_recordatorio_jefe(
    titulo: str,
    nombre: str,
    area_nombre: str,
    tipo_informe: int,
    fecha_entrega: str,
) -> tuple[str, str]:
    """Recordatorio al jefe de área: faltan 2 días para entregar su informe."""
    nombre_informe = NOMBRE_INFORME.get(tipo_informe, f"Informe {tipo_informe}")
    asunto = f"Recordatorio: {nombre_informe} — entrega el {fecha_entrega}"

    cuerpo = (
        _p(f"Estimado/a {_tratamiento(titulo)}{escape(nombre)}:")
        + _p("Reciba un cordial saludo.")
        + _p(
            f"Le recordamos que la entrega del <strong>{escape(nombre_informe)}</strong> "
            f"correspondiente al Área de <strong>{escape(area_nombre)}</strong> está prevista "
            f"para el <strong>{escape(fecha_entrega)}</strong>, es decir, en dos días."
        )
        + _p("Para completarlo, debe ingresar al sistema y:")
        + _lista(_TAREAS_JEFE.get(tipo_informe, ["Completar y generar el informe de su área."]))
        + _p(
            "Una vez completado, puede generar el documento y descargarlo desde la sección "
            "de informes."
        )
        + _p("Agradezco de antemano su puntualidad y colaboración.")
        + _firma("Dirección de Carrera", "Dirección de Carrera")
    )
    return asunto, cuerpo


def correo_recordatorio_docente(
    titulo: str,
    nombre: str,
    materias: list[str],
    fecha_entrega: str,
    url_sistema: str,
) -> tuple[str, str]:
    """Recordatorio al docente: registrar sus aportes antes de que cierre el informe."""
    asunto = f"Recordatorio: observaciones y acciones de mejora — hasta el {fecha_entrega}"

    listado = _lista([escape(m) for m in materias]) if materias else ""
    url = escape(url_sistema)

    cuerpo = (
        _p(f"Estimado/a {_tratamiento(titulo)}{escape(nombre)}:")
        + _p("Reciba un cordial saludo.")
        + _p(
            "Le recordamos que el <strong>"
            f"{escape(fecha_entrega)}</strong> cierra el plazo para registrar sus "
            "<strong>observaciones</strong> y <strong>acciones de mejora</strong> sobre las "
            "asignaturas que imparte, que se incorporarán a los informes de seguimiento "
            f"académico de la {CARRERA}."
        )
        + (_p("Asignaturas a su cargo:") + listado if materias else "")
        + _p(
            "Puede registrarlas ingresando al sistema, en las secciones "
            "<strong>Observaciones</strong> y <strong>Acciones de mejora</strong> de su panel. "
            "Cada registro se acumula, de modo que puede añadir varios a lo largo del período."
        )
        + _p(
            "En caso de que lo considere pertinente, puede ingresar sus sugerencias en el "
            f'siguiente enlace: <a href="{url}">{url}</a>.'
        )
        + _p(
            "Si aún no cuenta con una cuenta en el sistema, puede solicitarla en la "
            "Dirección de Carrera."
        )
        + _p(
            "Su aporte constituye un insumo de gran valor para el análisis y el fortalecimiento "
            "continuo de la carrera."
        )
        + _firma("Dirección de Carrera", "Dirección de Carrera")
    )
    return asunto, cuerpo


# ──────────────────────────────────────────────────────────────────
# Cargo legible del remitente
# ──────────────────────────────────────────────────────────────────

_CARGOS = {
    "DIRECTOR_CARRERA": "Dirección de Carrera",
    "JEFE_AREA": "Jefatura de Área",
    "DOCENTE": "Docente",
}


def cargo_de_rol(rol: str, area_nombre: str | None = None) -> str:
    """Texto del `[Cargo]` de la firma, a partir del rol efectivo del remitente."""
    if rol == "JEFE_AREA" and area_nombre:
        return f"Jefatura de Área de {area_nombre}"
    return _CARGOS.get(rol, "Carrera de Ciencias de la Computación")
