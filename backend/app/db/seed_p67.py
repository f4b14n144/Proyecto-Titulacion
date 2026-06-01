"""
Carga de datos reales del Período 67 — Carrera de Computación UPS Cuenca.

Ejecutar DESPUÉS de seed.py (roles, admin, áreas base):
  docker compose exec backend python -m app.db.seed_p67

Crea:
  - Período académico "2025-2026 (67)" activo
  - Consejo de Carrera de prueba
  - 44 asignaturas asignadas a las 5 áreas
  - 39 docentes con rol DOCENTE
  - 83 asignaciones docente-asignatura-grupo
"""
import re
import app.db.base  # noqa: F401 — carga todos los modelos para SQLAlchemy
from app.db.session import SessionLocal
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.periodo import PeriodoAcademico
from app.models.consejo import ConsejoCarrera
from app.models.area import Area
from app.models.asignatura import Asignatura
from app.models.asignacion import AsignacionDocente
from app.core.security import hash_password
from datetime import date


# ──────────────────────────────────────────────────────────────────
# Mapeo asignaturas → área (basado en estructura curricular UPS)
# ──────────────────────────────────────────────────────────────────
AREA_ASIGNATURAS: dict[str, list[str]] = {
    "Ciencias Básicas": [
        "CÁLCULO DIFERENCIAL", "CÁLCULO INTEGRAL", "ÁLGEBRA LINEAL",
        "ECUACIONES DIFERENCIALES", "PROBABILIDAD Y ESTADÍSTICA", "MÉTODOS NUMÉRICOS",
        "FÍSICA PARA CIENCIAS DE LA COMPUTACIÓN",
        "INTRODUCCIÓN A LA FÍSICA PARA CIENCIAS DE LA COMPUTACIÓN",
        "ELECTROTECNIA", "ELECTRÓNICA",
    ],
    "Programación y Software": [
        "PROGRAMACIÓN", "PROGRAMACIÓN ORIENTADA A OBJETOS", "PROGRAMACIÓN APLICADA",
        "PROGRAMACIÓN Y PLATAFORMAS WEB", "ESTRUCTURA DE DATOS",
        "ARQUITECTURA DEL COMPUTADOR", "SIMULACIÓN",
    ],
    "Redes y Comunicaciones": [
        "REDES DE COMPUTADORAS I", "REDES DE COMPUTADORAS II",
        "SISTEMAS DISTRIBUIDOS", "SISTEMAS EMBEBIDOS", "COMPUTACIÓN PARALELA",
        "ADMINISTRACIÓN DE SISTEMAS OPERATIVOS", "FUNDAMENTOS DE SISTEMAS OPERATIVOS",
    ],
    "Sistemas de Información": [
        "FUNDAMENTOS DE BASE DE DATOS", "GESTIÓN DE BASE DE DATOS",
        "SEGURIDAD DE LA INFORMACIÓN", "GESTIÓN EMPRESARIAL",
    ],
    "Inteligencia Artificial y Datos": [
        "INTELIGENCIA ARTIFICIAL", "APRENDIZAJE AUTOMÁTICO", "MINERÍA DE DATOS",
        "VISIÓN POR COMPUTADOR",
        "ANÁLISIS MULTIVARIADO Y MODELOS ESTOCÁSTICOS",
    ],
}

# Asignaturas generales / humanidades / titulación
AREA_GENERAL = "Ciencias Básicas"  # placeholder para materias sin área clara
ASIGNATURAS_GENERALES = [
    "ÉTICA", "PENSAMIENTO CRÍTICO", "PENSAMIENTO SOCIAL DE LA IGLESIA",
    "VIDA Y TRASCENDENCIA", "COMUNICACIÓN ORAL Y ESCRITA",
    "ANTROPOLOGÍA FILOSÓFICO-TEOLÓGICA",
    "PRÁCTICAS PRE PROFESIONALES", "PRÁCTICAS DE SERVICIO COMUNITARIO",
    "TRABAJO DE TITULACIÓN", "INTEGRACIÓN CURRICULAR", "PROYECTOS",
]

# Codigos de asignatura (simplificados)
def _codigo(nombre: str) -> str:
    palabras = [p for p in re.sub(r"[AEIOUÁÉÍÓÚÜ\s]", "", nombre.upper()) if p.isalpha()]
    base = "".join(palabras[:4])
    return f"INF-{base[:4].ljust(4,'X')}"


# Asignaciones datos reales (83 combinaciones del Período 67)
ASIGNACIONES_P67 = [
    ("TACURI CAPELO BERTHA KATERINE", "ADMINISTRACIÓN DE SISTEMAS OPERATIVOS", "G1"),
    ("LEGUIZAMO BOHORQUEZ MARIA ANAIS", "ANTROPOLOGÍA FILOSÓFICO-TEOLÓGICA", "G11"),
    ("LEGUIZAMO BOHORQUEZ MARIA ANAIS", "ANTROPOLOGÍA FILOSÓFICO-TEOLÓGICA", "G12"),
    ("SAMANIEGO SAGBAY VICENTE RIGOBERTO", "ANTROPOLOGÍA FILOSÓFICO-TEOLÓGICA", "G13"),
    ("ORDOÑEZ JARA MARCO VINICIO", "ANTROPOLOGÍA FILOSÓFICO-TEOLÓGICA", "G53"),
    ("HURTADO ORTIZ REMIGIO ISMAEL", "ANÁLISIS MULTIVARIADO Y MODELOS ESTOCÁSTICOS", "G1"),
    ("HURTADO ORTIZ REMIGIO ISMAEL", "APRENDIZAJE AUTOMÁTICO", "G1"),
    ("FLORES VAZQUEZ MARCELO ESTEBAN", "ARQUITECTURA DEL COMPUTADOR", "G1"),
    ("LEON PAREDES GABRIEL ALEJANDRO", "COMPUTACIÓN PARALELA", "G1"),
    ("ALVAREZ TORRES CARMEN ROSA", "COMUNICACIÓN ORAL Y ESCRITA", "G1"),
    ("CEVALLOS LUDEÑA CINTHYA MARIA", "COMUNICACIÓN ORAL Y ESCRITA", "G2"),
    ("CEVALLOS LUDEÑA CINTHYA MARIA", "COMUNICACIÓN ORAL Y ESCRITA", "G3"),
    ("SANMARTIN GARCIA BRIGIDA XIMENA", "COMUNICACIÓN ORAL Y ESCRITA", "G33"),
    ("PINOS VELEZ EDUARDO GUILLERMO", "CÁLCULO DIFERENCIAL", "G22"),
    ("VERDUGO ROMERO WALTER ENRIQUE", "CÁLCULO DIFERENCIAL", "G4"),
    ("VERDUGO ROMERO WALTER ENRIQUE", "CÁLCULO DIFERENCIAL", "G5"),
    ("BRAVO QUEZADA OMAR GUSTAVO", "CÁLCULO DIFERENCIAL", "G6"),
    ("VERDUGO ROMERO WALTER ENRIQUE", "CÁLCULO INTEGRAL", "G2"),
    ("JARA SALTOS JUAN DIEGO", "ECUACIONES DIFERENCIALES", "G10"),
    ("PERALTA SEVILLA ARTURO GEOVANNY", "ECUACIONES DIFERENCIALES", "G2"),
    ("QUINTUÑA PADILLA WILSON PATRICIO", "ELECTROTECNIA", "G1"),
    ("QUINTUÑA PADILLA WILSON PATRICIO", "ELECTRÓNICA", "G1"),
    ("FLORES VAZQUEZ MARCELO ESTEBAN", "ELECTRÓNICA", "G2"),
    ("QUINTUÑA PADILLA WILSON PATRICIO", "ELECTRÓNICA", "G3"),
    ("TORRES PEÑA PABLO ANDRES", "ESTRUCTURA DE DATOS", "G1"),
    ("YEPEZ ALULEMA JENNIFER ANDREA", "FUNDAMENTOS DE BASE DE DATOS", "G1"),
    ("TACURI CAPELO BERTHA KATERINE", "FUNDAMENTOS DE SISTEMAS OPERATIVOS", "G1"),
    ("LOAIZA MARTINEZ MARIA DE LOURDES", "FUNDAMENTOS DE SISTEMAS OPERATIVOS", "G2"),
    ("VILORIA AVILA TONY JESUS", "FÍSICA PARA CIENCIAS DE LA COMPUTACIÓN", "G1"),
    ("PARRA GONZALEZ GERMAN ERNESTO", "GESTIÓN DE BASE DE DATOS", "G1"),
    ("PARRA GONZALEZ GERMAN ERNESTO", "GESTIÓN DE BASE DE DATOS", "G2"),
    ("VIVAR BRAVO FERNANDO ANDRES", "GESTIÓN EMPRESARIAL", "G1"),
    ("HURTADO ORTIZ REMIGIO ISMAEL", "INTEGRACIÓN CURRICULAR", "G1"),
    ("HURTADO ORTIZ REMIGIO ISMAEL", "INTELIGENCIA ARTIFICIAL", "G1"),
    ("ORDOÑEZ ORDOÑEZ JORGE OSMANI", "INTRODUCCIÓN A LA FÍSICA PARA CIENCIAS DE LA COMPUTACIÓN", "G1"),
    ("ORDOÑEZ ORDOÑEZ JORGE OSMANI", "INTRODUCCIÓN A LA FÍSICA PARA CIENCIAS DE LA COMPUTACIÓN", "G2"),
    ("ORDOÑEZ ORDOÑEZ JORGE OSMANI", "INTRODUCCIÓN A LA FÍSICA PARA CIENCIAS DE LA COMPUTACIÓN", "G3"),
    ("ORDOÑEZ ORDOÑEZ JORGE OSMANI", "INTRODUCCIÓN A LA FÍSICA PARA CIENCIAS DE LA COMPUTACIÓN", "G7"),
    ("BOJORQUE CHASI RODOLFO XAVIER", "MINERÍA DE DATOS", "G1"),
    ("GARCIA VELEZ ROBERTO AGUSTIN", "MÉTODOS NUMÉRICOS", "G2"),
    ("ALTAMIRANO SANCHEZ JORGE IVAN", "PENSAMIENTO CRÍTICO", "G5"),
    ("PORTILLA FARFAN FREDI LEONIDAS", "PENSAMIENTO CRÍTICO", "G6"),
    ("RIERA PORTOVIEJO VERONICA MARIBEL", "PENSAMIENTO SOCIAL DE LA IGLESIA", "G6"),
    ("BRAVO QUEZADA OMAR GUSTAVO", "PROBABILIDAD Y ESTADÍSTICA", "G1"),
    ("SACOTO CABRERA ERWIN JAIRO", "PROBABILIDAD Y ESTADÍSTICA", "G2"),
    ("MORQUECHO YUNGA MARIA DEL PILAR", "PROGRAMACIÓN", "G1"),
    ("ARCOS ARGUDO MIGUEL ARTURO", "PROGRAMACIÓN", "G2"),
    ("LOAIZA MARTINEZ MARIA DE LOURDES", "PROGRAMACIÓN", "G23"),
    ("ARCE CUESTA DIANA CAROLINA", "PROGRAMACIÓN", "G3"),
    ("PLAZA CORDERO ANDREA MARICELA", "PROGRAMACIÓN APLICADA", "G1"),
    ("PLAZA CORDERO ANDREA MARICELA", "PROGRAMACIÓN APLICADA", "G2"),
    ("LOAIZA MARTINEZ MARIA DE LOURDES", "PROGRAMACIÓN ORIENTADA A OBJETOS", "G1"),
    ("TIMBI SISALIMA CRISTIAN FERNANDO", "PROGRAMACIÓN Y PLATAFORMAS WEB", "G1"),
    ("TORRES PEÑA PABLO ANDRES", "PROGRAMACIÓN Y PLATAFORMAS WEB", "G2"),
    ("VIVAR BRAVO FERNANDO ANDRES", "PROYECTOS", "G6"),
    ("GARCIA VELEZ ROBERTO AGUSTIN", "PRÁCTICAS DE SERVICIO COMUNITARIO", "G1"),
    ("GARCIA VELEZ ROBERTO AGUSTIN", "PRÁCTICAS PRE PROFESIONALES", "G1"),
    ("SACOTO CABRERA ERWIN JAIRO", "REDES DE COMPUTADORAS I", "G1"),
    ("GARCIA VELEZ ROBERTO AGUSTIN", "REDES DE COMPUTADORAS II", "G1"),
    ("GARCIA VELEZ ROBERTO AGUSTIN", "REDES DE COMPUTADORAS II", "G2"),
    ("YEPEZ ALULEMA JENNIFER ANDREA", "SEGURIDAD DE LA INFORMACIÓN", "G1"),
    ("TORRES PEÑA PABLO ANDRES", "SIMULACIÓN", "G1"),
    ("TIMBI SISALIMA CRISTIAN FERNANDO", "SISTEMAS DISTRIBUIDOS", "G1"),
    ("FLORES VAZQUEZ MARCELO ESTEBAN", "SISTEMAS EMBEBIDOS", "G1"),
    ("FLORES VAZQUEZ MARCELO ESTEBAN", "SISTEMAS EMBEBIDOS", "G2"),
    ("LEON PAREDES GABRIEL ALEJANDRO", "TRABAJO DE TITULACIÓN", "G1"),
    ("TACURI CAPELO BERTHA KATERINE", "TRABAJO DE TITULACIÓN", "G1"),
    ("GUZMAN RUIZ LOURDES JANNETH", "VIDA Y TRASCENDENCIA", "G11"),
    ("GUZMAN RUIZ LOURDES JANNETH", "VIDA Y TRASCENDENCIA", "G12"),
    ("ROBLES BYKBAEV VLADIMIR ESPARTACO", "VISIÓN POR COMPUTADOR", "G1"),
    ("MORQUECHO YUNGA MARIA DEL PILAR", "ÁLGEBRA LINEAL", "G21"),
    ("ARMIJOS CORDERO XAVIER LEONARDO", "ÁLGEBRA LINEAL", "G3"),
    ("MORQUECHO YUNGA MARIA DEL PILAR", "ÁLGEBRA LINEAL", "G4"),
    ("MORQUECHO YUNGA MARIA DEL PILAR", "ÁLGEBRA LINEAL", "G5"),
    ("ROJAS ABRIL PAOLA DEL CARMEN", "ÉTICA", "G7"),
    # Docentes adicionales con asignaturas generales sin grupo específico de calificaciones
    ("PEREZ MUÑOZ ANGEL ANDRES", "INTEGRACIÓN CURRICULAR", "G2"),
    ("GARCIA VELEZ ROBERTO AGUSTIN", "INTEGRACIÓN CURRICULAR", "G3"),
    ("BRAVO QUEZADA OMAR GUSTAVO", "INTEGRACIÓN CURRICULAR", "G4"),
    ("TIMBI SISALIMA CRISTIAN FERNANDO", "INTEGRACIÓN CURRICULAR", "G5"),
    ("FLORES VAZQUEZ MARCELO ESTEBAN", "INTEGRACIÓN CURRICULAR", "G6"),
    ("ROBLES BYKBAEV VLADIMIR ESPARTACO", "INTEGRACIÓN CURRICULAR", "G7"),
    ("TORRES PEÑA PABLO ANDRES", "PROGRAMACIÓN", "G23"),
]


def _nombre_a_email(nombre: str) -> str:
    """Genera email institucional desde nombre completo."""
    partes = nombre.lower().split()
    if len(partes) >= 2:
        return f"{partes[0]}.{partes[-1]}@ups.edu.ec"
    return f"{partes[0]}@ups.edu.ec"


def seed_p67():
    db = SessionLocal()
    try:
        # ── Período 67 ────────────────────────────────────────────
        periodo = db.query(PeriodoAcademico).filter(
            PeriodoAcademico.nombre == "2025-2026 (67)"
        ).first()
        if not periodo:
            periodo = PeriodoAcademico(
                nombre="2025-2026 (67)",
                fecha_inicio=date(2025, 9, 1),
                fecha_fin=date(2026, 2, 28),
                activo=True,
            )
            db.add(periodo)
            db.flush()
            print(f"  Período creado: {periodo.nombre} (id={periodo.id})")
        else:
            print(f"  Período ya existe: {periodo.nombre}")

        # Desactivar otros períodos
        db.query(PeriodoAcademico).filter(
            PeriodoAcademico.id != periodo.id, PeriodoAcademico.activo == True
        ).update({"activo": False})

        # ── Consejo de prueba ─────────────────────────────────────
        consejo = db.query(ConsejoCarrera).filter(
            ConsejoCarrera.periodo_id == periodo.id
        ).first()
        if not consejo:
            consejo = ConsejoCarrera(
                periodo_id=periodo.id,
                fecha_consejo=date(2026, 1, 15),
                fecha_limite_informe=date(2026, 2, 15),
                fecha_activacion=date(2026, 2, 13),
                flujo_estado="PENDIENTE",
            )
            db.add(consejo)
            db.flush()
            print(f"  Consejo creado (id={consejo.id})")

        # ── Áreas ─────────────────────────────────────────────────
        areas_db: dict[str, Area] = {}
        for nombre_area in list(AREA_ASIGNATURAS.keys()) + ["Humanidades y Titulación"]:
            area = db.query(Area).filter(Area.nombre == nombre_area).first()
            if not area:
                area = Area(nombre=nombre_area)
                db.add(area)
                db.flush()
                print(f"  Área creada: {nombre_area}")
            areas_db[nombre_area] = area

        # ── Asignaturas ───────────────────────────────────────────
        # Construir mapa inverso asignatura → área
        asig_a_area: dict[str, str] = {}
        for area_nombre, lista in AREA_ASIGNATURAS.items():
            for asig in lista:
                asig_a_area[asig.upper()] = area_nombre
        for asig in ASIGNATURAS_GENERALES:
            asig_a_area[asig.upper()] = "Humanidades y Titulación"

        asignaturas_db: dict[str, Asignatura] = {}
        nombres_asig_vistos: set[str] = set()
        for docente_nombre, asig_nombre, grupo in ASIGNACIONES_P67:
            if asig_nombre in nombres_asig_vistos:
                continue
            nombres_asig_vistos.add(asig_nombre)

            area_nombre = asig_a_area.get(asig_nombre.upper(), "Ciencias Básicas")
            area = areas_db.get(area_nombre) or areas_db["Ciencias Básicas"]

            codigo = _codigo(asig_nombre)
            # Asegurar unicidad del código
            sufijo = 0
            codigo_final = codigo
            while db.query(Asignatura).filter(Asignatura.codigo == codigo_final).first():
                sufijo += 1
                codigo_final = f"{codigo}{sufijo}"

            asig = db.query(Asignatura).filter(Asignatura.nombre == asig_nombre).first()
            if not asig:
                asig = Asignatura(area_id=area.id, nombre=asig_nombre, codigo=codigo_final)
                db.add(asig)
                db.flush()
                print(f"  Asignatura: [{codigo_final}] {asig_nombre} → {area_nombre}")
            asignaturas_db[asig_nombre] = asig

        # ── Rol DOCENTE ───────────────────────────────────────────
        rol_docente = db.query(Rol).filter(Rol.nombre == "DOCENTE").first()
        if not rol_docente:
            raise ValueError("Rol DOCENTE no encontrado. Ejecutar seed.py primero.")

        # ── Docentes ──────────────────────────────────────────────
        docentes_db: dict[str, Usuario] = {}
        nombres_docentes = list({d for d, _, _ in ASIGNACIONES_P67})
        for nombre in sorted(nombres_docentes):
            email = _nombre_a_email(nombre)
            usuario = db.query(Usuario).filter(Usuario.email_institucional == email).first()
            if not usuario:
                usuario = Usuario(
                    nombre_completo=nombre.title(),
                    email_institucional=email,
                    hashed_password=hash_password("docente1234"),
                    rol_id=rol_docente.id,
                    activo=True,
                )
                db.add(usuario)
                db.flush()
                print(f"  Docente: {nombre.title()} ({email})")
            docentes_db[nombre] = usuario

        # ── Asignaciones ──────────────────────────────────────────
        creadas = 0
        omitidas = 0
        for docente_nombre, asig_nombre, grupo in ASIGNACIONES_P67:
            docente = docentes_db.get(docente_nombre)
            asig = asignaturas_db.get(asig_nombre)
            if not docente or not asig:
                print(f"  WARN: no encontrado {docente_nombre} | {asig_nombre}")
                continue

            existe = db.query(AsignacionDocente).filter(
                AsignacionDocente.usuario_id == docente.id,
                AsignacionDocente.asignatura_id == asig.id,
                AsignacionDocente.periodo_id == periodo.id,
                AsignacionDocente.grupo == grupo,
            ).first()
            if not existe:
                db.add(AsignacionDocente(
                    usuario_id=docente.id,
                    asignatura_id=asig.id,
                    periodo_id=periodo.id,
                    grupo=grupo,
                ))
                creadas += 1
            else:
                omitidas += 1

        db.commit()
        print(f"\nSeed P67 completado:")
        print(f"  - Período: 2025-2026 (67) activo")
        print(f"  - Áreas: {len(areas_db)}")
        print(f"  - Asignaturas: {len(asignaturas_db)}")
        print(f"  - Docentes: {len(docentes_db)}")
        print(f"  - Asignaciones creadas: {creadas}, omitidas (ya existían): {omitidas}")
        print(f"\nConsejo id={consejo.id} para subir calificaciones.")
        print(f"Credenciales docentes: email generado / docente1234")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_p67()
