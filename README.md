# Sistema de Informes Académicos UPS Cuenca

Sistema web para automatizar la generación de informes de seguimiento académico
de la Carrera de Computación UPS Cuenca, requeridos por el proceso de acreditación CACES.

## Requisitos

- Docker Desktop 24+
- Docker Compose v2+
- Git

No se requiere instalar Node.js ni Python en el host.

## Arranque rápido

```bash
# 1. Clonar el repositorio
git clone https://github.com/f4b14n144/Proyecto-Titulacion.git
cd Proyecto-Titulacion

# 2. Crear el archivo de variables de entorno
cp .env.example .env
# Editar .env con tus credenciales reales

# 3. Levantar todos los servicios
docker compose up --build -d

# 4. Aplicar migraciones de base de datos
docker compose exec backend alembic upgrade head

# 5. Cargar datos iniciales (roles, admin, áreas)
docker compose exec backend python -m app.db.seed

# 6. Generar las plantillas .docx base (Jinja2) — requerido para informes con formato
docker compose exec backend python app/static/plantillas/crear_plantillas.py

# 7. (Opcional) Datos reales del Período 67 para pruebas
docker compose exec backend python -m app.db.seed_p67
# 8. (Opcional) Cuentas de prueba por rol (director / jefe / docente)
docker compose exec backend python -m app.db.seed_test_users
```

> **Nota:** las plantillas `.docx` se generan con el script (paso 6) y no se
> versionan en el repo. Sin ellas, los informes salen con un formato básico de
> respaldo en lugar del formato institucional completo.

## URLs

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost |
| API | http://localhost/api/v1 |
| Docs API | http://localhost/docs |
| Backend directo | http://localhost:8000 |
| Frontend directo | http://localhost:5173 |

## Credenciales por defecto (solo desarrollo)

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| director@ups.edu.ec | admin1234 | Director de Carrera |

**Cambiar la contraseña inmediatamente en producción.**

## Variables de entorno obligatorias

Copiar `.env.example` a `.env` y completar:

```
DATABASE_URL=postgresql://usuario:password@postgres:5432/informes_db
SECRET_KEY=<generar con: openssl rand -hex 32>
ANTHROPIC_API_KEY=sk-ant-...
SMTP_USER=<cuenta Brevo>
SMTP_PASSWORD=<clave Brevo>
REPLY_TO_DOMAIN=<dominio para emails de respuesta>
```

## Estructura

```
├── backend/          FastAPI + SQLAlchemy + Alembic
├── frontend/         React + TypeScript + Vite + Tailwind
├── nginx/            Reverse proxy
├── docs/             Sprint log, decisiones, pendientes
├── CLAUDE.md         Estado del proyecto para sesiones AI
└── docker-compose.yml
```

## Sprints

| Sprint | Objetivo | Estado |
|--------|----------|--------|
| 0 | Entorno base: Docker, auth, estructura | ✅ Completado |
| 1 | Panel director: períodos, consejos, Excel | 🔄 Siguiente |
| 2 | Scheduler, correo, generación Word | ⏳ Pendiente |
| 3 | Integración IA, informes completos | ⏳ Pendiente |
| 4 | Pruebas con datos reales P67 | ⏳ Pendiente |
| 5 | Ajustes finales, demo Taller Pitch 15-16/07/2026 | ⏳ Pendiente |

## Comandos útiles

```bash
# Ver logs del backend
docker compose logs -f backend

# Acceder al backend
docker compose exec backend bash

# Crear nueva migración
docker compose exec backend alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
docker compose exec backend alembic upgrade head

# Detener todos los servicios
docker compose down
```
