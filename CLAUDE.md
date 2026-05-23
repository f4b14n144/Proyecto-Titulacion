# CLAUDE.md — Estado del Proyecto
# Sistema de Informes Académicos UPS Cuenca — Tesis P68

---

## REGLA: Al iniciar cada sesión
1. Leer este archivo completo
2. Leer docs/sprint-log.md
3. Leer docs/pending.md
4. Anunciar: "Retomando desde: [tarea]. Voy a hacer: [descripción exacta]."
5. Esperar confirmación de Fabian antes de empezar
6. Trabajar UNA tarea a la vez

---

## Estado general
Fecha última actualización: 2026-05-23
Sprint activo: 1 (Sprint 0 completado)
Rama Git: main
Repo: https://github.com/f4b14n144/Proyecto-Titulacion.git

---

## Próxima tarea al iniciar
**S1-01** — CRUD de períodos académicos
- Backend: crear `backend/app/api/v1/endpoints/periodos.py` + `backend/app/schemas/periodo.py`
- Registrar el router en `backend/app/api/v1/api_router.py`

---

## Si la sesión se cortó a medias
Archivo: —
Línea aproximada: —
Qué faltaba completar: —

---

## SPRINT 0 — COMPLETADO ✅
Objetivo: entorno funcional con frontend, backend y DB conectados

- [x] S0-01: Verificado Docker 29.4.3, Git 2.54; Node/Python van dentro de Docker
- [x] S0-02: Estructura completa de carpetas creada
- [x] S0-03: git init + remote → https://github.com/f4b14n144/Proyecto-Titulacion.git
- [x] S0-04: CLAUDE.md, docs/sprint-log.md, docs/pending.md, docs/decisions.md
- [x] S0-05: docker-compose.yml (postgres + backend + frontend + nginx)
- [x] S0-06: .env.example con todas las variables
- [x] S0-07: backend/Dockerfile (python:3.11-slim)
- [x] S0-08: backend/requirements.txt (FastAPI, SQLAlchemy, Alembic, pydantic v2, LiteLLM, etc.)
- [x] S0-09: backend/app/core/config.py (Settings con pydantic-settings)
- [x] S0-10: backend/app/db/session.py + base.py (SQLAlchemy)
- [x] S0-11: 14 modelos SQLAlchemy en backend/app/models/ (un archivo por tabla)
- [x] S0-12: backend/app/main.py (FastAPI + CORS + router)
- [x] S0-13: GET /api/v1/health (verifica conexión DB)
- [x] S0-14: Alembic configurado (alembic.ini + env.py que lee DATABASE_URL del entorno)
- [x] S0-15: Migración inicial "001_init_schema_completo" con las 14 tablas
- [x] S0-16: backend/app/db/seed.py (roles, admin director@ups.edu.ec/admin1234, 5 áreas)
- [x] S0-17: backend/app/core/security.py (JWT + bcrypt) + endpoints auth (login, refresh, me)
- [x] S0-18: backend/app/core/deps.py (get_db, get_current_user, require_role)
- [x] S0-19: backend/app/schemas/auth.py + schemas/usuario.py (Pydantic v2)
- [x] S0-20: backend/app/api/v1/endpoints/usuarios.py (CRUD protegido por DIRECTOR_CARRERA)
- [x] S0-21: frontend/ inicializado (React + TypeScript + Vite)
- [x] S0-22: TailwindCSS configurado con colores UPS (ups-blue, ups-red)
- [x] S0-23: React Router v6 con rutas base y ProtectedRoute por rol
- [x] S0-24: frontend/src/services/api.ts (Axios + interceptor JWT + auto-refresh)
- [x] S0-25: frontend/src/pages/auth/Login.tsx conectada al backend
- [x] S0-26: Dashboard director y jefe + Navbar + Sidebar con links por rol
- [x] S0-27: frontend/Dockerfile (node:20-alpine)
- [x] S0-28: nginx/nginx.conf (reverse proxy API + frontend + static docx)
- [x] S0-29: docker compose up —build funciona (verificado localmente)
- [x] S0-30: Login end-to-end funciona desde el frontend
- [x] S0-31: README.md con instrucciones completas
- [x] S0-32: CLAUDE.md actualizado — Sprint 0 COMPLETADO

---

## SPRINT 1 — EN CURSO 🔄
Objetivo: director puede configurar todo el sistema y subir calificaciones

- [ ] S1-01: CRUD períodos académicos (backend: endpoints + schemas)
- [ ] S1-02: Pantalla Periodos.tsx funcional en panel director
- [ ] S1-03: CRUD Consejos de Carrera con fechas (backend)
- [ ] S1-04: Pantalla Consejos.tsx funcional
- [ ] S1-05: CRUD áreas curriculares (backend)
- [ ] S1-06: Pantalla Areas.tsx funcional
- [ ] S1-07: CRUD asignaturas con asignación a área (backend)
- [ ] S1-08: Pantalla Asignaturas.tsx
- [ ] S1-09: Endpoints jefaturas de área con validaciones de unicidad
- [ ] S1-10: Pantalla asignación de jefaturas
- [ ] S1-11: Endpoints asignaciones docente-asignatura-grupo por período
- [ ] S1-12: Pantalla asignaciones docente
- [ ] S1-13: Endpoint gestión completa de usuarios con filtros
- [ ] S1-14: Pantalla Usuarios.tsx funcional
- [ ] S1-15: excel_processor.py — leer Excel, detectar columnas
- [ ] S1-16: excel_processor.py — filtrar calificaciones por área
- [ ] S1-17: excel_processor.py — estructurar datos en JSON
- [ ] S1-18: Endpoint POST /calificaciones/subir (.xlsx + tipo + consejo_id)
- [ ] S1-19: Pantalla SubirCalificaciones.tsx con preview
- [ ] S1-20: Panel jefe de área — vista de informes con estados
- [ ] S1-21: Verificación completa Sprint 1
- [ ] S1-22: Actualizar CLAUDE.md Sprint 1 completado

---

## SPRINTS PENDIENTES
- Sprint 2: Scheduler, correo SMTP/IMAP, generación .docx
- Sprint 3: IA (LiteLLM), informes 1-4 completos
- Sprint 4: Pruebas con datos reales Período 67
- Sprint 5: Ajustes finales, demo Taller Pitch 15-16/07/2026

---

## Arquitectura actual del proyecto

### Para levantar el sistema
```
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.db.seed
# → http://localhost  (login: director@ups.edu.ec / admin1234)
```

### Backend — archivos clave
```
backend/app/main.py              FastAPI entry point, CORS, router
backend/app/core/config.py       Settings (pydantic-settings, lee .env)
backend/app/core/security.py     JWT (jose) + bcrypt (passlib)
backend/app/core/deps.py         get_db, get_current_user, require_role
backend/app/db/base.py           Base declarativa + imports de todos los modelos
backend/app/db/session.py        engine + SessionLocal
backend/app/db/seed.py           Datos iniciales
backend/app/models/              14 modelos (un .py por tabla)
backend/app/schemas/             auth.py, usuario.py
backend/app/api/v1/api_router.py Router principal
backend/app/api/v1/endpoints/    health.py, auth.py, usuarios.py
backend/alembic/versions/001_... Migración inicial completa
```

### Frontend — archivos clave
```
frontend/src/main.tsx            Entry point, BrowserRouter, AuthCtx.Provider
frontend/src/App.tsx             Rutas (director/*, jefe/*, login, /)
frontend/src/hooks/useAuth.ts    AuthCtx + useAuthProvider + useAuth
frontend/src/services/api.ts     Axios + interceptor JWT + auto-refresh
frontend/src/services/auth.service.ts login, me, logout
frontend/src/components/         Navbar, Sidebar, ProtectedRoute
frontend/src/pages/auth/         Login.tsx
frontend/src/pages/director/     Dashboard + 7 placeholders Sprint 1+
frontend/src/pages/jefe_area/    Dashboard + Informe2/3/4 placeholders
frontend/src/types/index.ts      Interfaces TypeScript (AuthUser, ApiResponse, etc.)
frontend/src/utils/formatters.ts formatFecha, formatEstado
```

### Convenciones de código
- Respuestas API: `{"data": ..., "message": "...", "success": bool}`
- Comentarios: en español
- Commits: `feat:` | `fix:` | `chore:` | `docs:`
- Pydantic v2: siempre `model_config = ConfigDict(...)`
- require_role: `require_role("DIRECTOR_CARRERA")` en endpoints protegidos

---

## Decisiones tomadas (no reabrir)
Ver docs/decisions.md para lista completa.
- Node.js y Python NO se instalan en el host; corren en Docker
- python-docx-template (NO python-docx puro)
- LiteLLM como librería Python (NO como proxy)
- PostgreSQL 15+ en dev y producción
- APScheduler embebido en FastAPI (un solo worker)

---

## Problemas conocidos / notas técnicas
- En Windows, git muestra warnings de LF→CRLF — es normal, no afecta el funcionamiento
- El archivo .env NO va al repo (está en .gitignore); .env.example sí va
- Para producción: cambiar SECRET_KEY con `openssl rand -hex 32`
