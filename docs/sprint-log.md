# Sprint Log

---

## 2026-05-23 — Sesión 1 y 2 — Sprint 0 completo

### Qué se hizo
**Sesión 1 (S0-01 a S0-16):**
- Verificado entorno: Docker 29.4.3 ✅, Git 2.54 ✅ (Node/Python van en Docker)
- Creada estructura completa de carpetas del proyecto
- `git init` + remote apuntando a https://github.com/f4b14n144/Proyecto-Titulacion.git
- CLAUDE.md, docs/ (sprint-log, pending, decisions)
- docker-compose.yml con postgres, backend, frontend, nginx
- .env.example con todas las variables
- backend/Dockerfile (python:3.11-slim)
- backend/requirements.txt (todas las dependencias del stack)
- backend/app/core/config.py (pydantic-settings)
- backend/app/db/session.py + base.py
- 14 modelos SQLAlchemy: rol, usuario, periodo, consejo, area, asignatura,
  jefatura, asignacion, calificacion, informe, checklist_avac,
  checklist_visita, notificacion, respuesta_docente
- backend/app/main.py (FastAPI + CORS)
- GET /api/v1/health
- Alembic configurado + migración inicial "001_init_schema_completo"
- backend/app/db/seed.py (roles, admin director@ups.edu.ec/admin1234, 5 áreas)
- Commit inicial pusheado a main

**Sesión 2 (S0-17 a S0-32):**
- backend/app/core/security.py (JWT + bcrypt)
- backend/app/core/deps.py (get_db, get_current_user, require_role)
- backend/app/schemas/auth.py + schemas/usuario.py (Pydantic v2)
- backend/app/api/v1/endpoints/auth.py (POST /login, POST /refresh, GET /me)
- backend/app/api/v1/endpoints/usuarios.py (CRUD completo, solo DIRECTOR_CARRERA)
- frontend/ completo: React + TypeScript + Vite + Tailwind
- frontend/src/main.tsx + App.tsx + rutas React Router v6
- Login.tsx conectada al backend, ProtectedRoute, Navbar, Sidebar
- useAuth hook con AuthContext + auto-refresh JWT
- Axios con interceptor JWT
- Dashboards director y jefe
- Todas las páginas placeholder (Sprint 1+)
- README.md completo
- Commit + push a main → Sprint 0 COMPLETADO

### Resultado
Sprint 0 completado al 100%. Dos commits en main.
Sistema levantable con `docker compose up --build -d`.

---

## Próxima sesión — Sprint 1 inicio

**Primera tarea: S1-01**
CRUD de períodos académicos
- `backend/app/api/v1/endpoints/periodos.py`
- `backend/app/schemas/periodo.py`
- Registrar en `api_router.py`
- Luego: pantalla `frontend/src/pages/director/Periodos.tsx` funcional (S1-02)
