# CLAUDE.md — Estado del Proyecto
# Sistema de Informes Académicos UPS Cuenca — Tesis P68

## Sesión actual
Fecha: 2026-05-23
Sprint activo: 0
Tarea activa: —  (Sesión 1 cerrada)
Rama Git: main

## Tarea en curso
—

## Si la sesión se cortó a medias
Archivo: —
Línea aproximada: —
Qué faltaba completar: —

## Próxima tarea
S1-01 — CRUD de períodos académicos (backend endpoints + schemas)
Archivo: backend/app/api/v1/endpoints/periodos.py + backend/app/schemas/periodo.py

## Tareas completadas (marcar con x)
- [x] S0-01: Verificar herramientas — Docker 29.4.3 ✅ | Git 2.54 ✅ | Node ❌ (no necesario en host, va en Docker) | Python ❌ (ídem)
- [x] S0-02: Crear estructura de carpetas completa
- [x] S0-03: Inicializar git + conectar a https://github.com/f4b14n144/Proyecto-Titulacion.git
- [x] S0-04: Crear CLAUDE.md y docs/ (sprint-log, pending, decisions)
- [x] S0-05: docker-compose.yml (postgres + backend + frontend + nginx)
- [x] S0-06: .env.example con todas las variables
- [x] S0-07: Dockerfile del backend (python:3.11-slim)
- [x] S0-08: requirements.txt con todas las dependencias
- [x] S0-09: config.py con Settings usando pydantic-settings
- [x] S0-10: session.py + base.py para SQLAlchemy
- [x] S0-11: Todos los modelos SQLAlchemy (14 tablas, un archivo por tabla)
- [x] S0-12: main.py con FastAPI, CORS y router
- [x] S0-13: Endpoint GET /api/v1/health
- [x] S0-14: Alembic configurado (alembic.ini + env.py)
- [x] S0-15: Migración inicial "001_init_schema_completo" creada manualmente
- [x] S0-16: seed.py (roles, admin director@ups.edu.ec/admin1234, 5 áreas base)
- [x] S0-17: auth.py — endpoints login, refresh, me
- [x] S0-18: deps.py — get_db, get_current_user, require_role
- [x] S0-19: schemas/auth.py + schemas/usuario.py
- [x] S0-20: usuarios.py — CRUD completo con protección DIRECTOR_CARRERA
- [x] S0-21 a S0-26: Frontend React + TypeScript + Vite + Tailwind + Router + Login + Dashboards
- [x] S0-27: Dockerfile frontend
- [x] S0-28: nginx.conf reverse proxy
- [x] S0-31: README.md
- [x] S0-32: CLAUDE.md actualizado — Sprint 0 COMPLETADO

## Sprint 0 — COMPLETADO ✅

Todos los archivos del Sprint 0 han sido creados y pusheados a main.

## Decisiones tomadas esta sesión
- Node.js y Python NO se instalan en el host Windows; todo corre dentro de contenedores Docker.
- Docker Compose es el único método de ejecución local y en producción.
- Rama principal: main (renombrada de master)

## Problemas encontrados
- Git en Windows requirió configurar user.email y user.name antes del primer commit.

---

## REGLA: Al iniciar cada sesión
1. Leer este archivo
2. Leer docs/sprint-log.md
3. Leer docs/pending.md
4. Identificar la próxima tarea pendiente
5. Anunciar: "Retomando desde: [tarea]. Voy a hacer: [descripción exacta]."
6. Esperar confirmación antes de empezar
