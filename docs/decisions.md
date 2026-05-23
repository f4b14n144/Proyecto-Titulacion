# Decisiones de Arquitectura — NO Reabrir

## Backend
- Python 3.11+, FastAPI, SQLAlchemy, Alembic, APScheduler embebido
- pandas + openpyxl para Excel
- python-docx-template (NO python-docx puro) para Word con Jinja2
- LiteLLM como librería Python (NO como proxy)
- python-jose + passlib+bcrypt para auth
- pydantic v2 con model_config = ConfigDict(...)
- loguru para logging

## Frontend
- React + TypeScript + Vite + TailwindCSS
- React Router v6, Axios + JWT interceptor

## Base de datos
- PostgreSQL 15+ en dev y producción
- DATABASE_URL en .env — nunca hardcodeado

## Correo
- Desarrollo: Brevo SMTP (free tier, 300 emails/día)
- Producción: Postfix+Dovecot en mismo VPS
- Reply-To único por notificación: respuestas+{uuid}@dominio.com
- Polling IMAP cada 15 minutos

## IA
- LiteLLM → claude-sonnet-4-20250514 por defecto
- Cambio de proveedor solo con variable ANTHROPIC_API_KEY

## Infraestructura
- Docker Compose completo
- Nginx reverse proxy
- VPS Hetzner CX22 (~4 EUR/mes)

## Convenciones de código
- Respuestas API: {"data": ..., "message": "...", "success": bool}
- Comentarios: en español
- Commits: feat: | fix: | chore: | docs:
