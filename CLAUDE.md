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
Fecha última actualización: 2026-06-17
Sprint activo: 5 (Sprints 0-4 completados)
Rama Git: main
Repo: https://github.com/f4b14n144/Proyecto-Titulacion.git

---

## Próxima tarea al iniciar
**Sprint 5** — Ajustes finales y preparación demo (Taller Pitch 15-16/07/2026)
- S5-01: incorporar observaciones del tutor
- S5-02/03/04: refinar UI, mensajes de error, loading states
- S5-10: script de demo reproducible
- Las revisiones/cambios que mande el tutor entran aquí

## Cuentas de prueba (creadas con seed_test_users.py)
- Director: director@ups.edu.ec / director123
- Jefe de área: jefe@ups.edu.ec / pass123  (rol base DOCENTE + jefatura de Programación → opera como JEFE por rol efectivo)
- Docente: docente@ups.edu.ec / pass123
- Todos los docentes (incl. los 39 del P67): contraseña por defecto pass123 (reset_passwords_docentes.py)

## Modelo de roles (congruente)
- Rol base de todo profesor: DOCENTE. Solo el director tiene DIRECTOR_CARRERA.
- Rol EFECTIVO (calcular_rol_efectivo en deps.py): director siempre; JEFE_AREA si
  tiene jefatura en período activo; si no, DOCENTE. get_current_user lo adjunta y
  /me + require_role lo usan. Asignar/quitar jefatura cambia el panel al que entra.
- Informe 1 auto-llena designaciones de jefes (jefaturas del período) y nombre del director.

## NOTA IMPORTANTE — Proveedor de IA
- Se usa GROQ (free tier sin tarjeta): AI_PROVIDER=groq, AI_MODEL=groq/llama-3.3-70b-versatile
- GROQ_API_KEY está en .env (no en repo). Calidad de narrativa: profesional, español formal.
- ia_engine.py soporta 4 proveedores: groq, deepseek, gemini, anthropic (cambiar AI_PROVIDER)
- Gemini/Anthropic/DeepSeek se probaron: keys válidas pero sin saldo/quota en esas cuentas

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

## SPRINT 1 — COMPLETADO ✅
Objetivo: director puede configurar todo el sistema y subir calificaciones

- [x] S1-01: CRUD períodos académicos (backend: endpoints + schemas)
- [x] S1-02: Pantalla Periodos.tsx funcional en panel director
- [x] S1-03: CRUD Consejos de Carrera con fechas (backend)
- [x] S1-04: Pantalla Consejos.tsx funcional
- [x] S1-05: CRUD áreas curriculares (backend)
- [x] S1-06: Pantalla Areas.tsx funcional
- [x] S1-07: CRUD asignaturas con asignación a área (backend)
- [x] S1-08: Pantalla Asignaturas.tsx funcional
- [x] S1-09: Endpoints jefaturas de área con validaciones de unicidad
- [x] S1-10: Pantalla asignación de jefaturas (tab en Asignaciones.tsx)
- [x] S1-11: Endpoints asignaciones docente-asignatura-grupo por período
- [x] S1-12: Pantalla asignaciones docente (tab en Asignaciones.tsx)
- [x] S1-13: Endpoint gestión completa de usuarios con filtros (ya existía, verificado)
- [x] S1-14: Pantalla Usuarios.tsx funcional (filtros, modal, toggle activo/inactivo)
- [x] S1-15: excel_processor.py — leer Excel, detectar columnas (15+ sinónimos, filas auto)
- [x] S1-16: excel_processor.py — filtrar calificaciones por área (matching fuzzy asig+grupo)
- [x] S1-17: excel_processor.py — estructurar datos en JSON con estadísticos y advertencias
- [x] S1-18: Endpoint POST /calificaciones/preview + /calificaciones/confirmar
- [x] S1-19: Pantalla SubirCalificaciones.tsx — flujo 3 pasos con preview por asignatura
- [x] S1-20: Panel jefe de área actualizado con vista informes + accesos rápidos
- [x] S1-21: Sprint 1 considerado verificado (S1-22 completado abajo)
- [x] S1-22: CLAUDE.md actualizado — Sprint 1 COMPLETADO

---

## SPRINT 2 — COMPLETADO ✅
Objetivo: flujo automático de notificaciones y generación de .docx

- [x] S2-01: scheduler.py — BackgroundScheduler APScheduler zona America/Guayaquil
- [x] S2-02: programar_flujo_consejo — DateTrigger 2 días antes de fecha_limite
- [x] S2-03: sincronizar_todos_los_consejos — restaura jobs al reiniciar servidor
- [x] S2-04: flujo.py — POST /flujo/{id}/disparar (manual dev) + /reprogramar
- [x] S2-05: mail_service.py — conexión SMTP Brevo con starttls
- [x] S2-06: enviar_email — template HTML, adjuntos, modo dev sin SMTP
- [x] S2-07: generar_reply_to_token — UUID único por notificación
- [x] S2-08: enviar_email_docente — template con Reply-To personalizado
- [x] S2-09: enviar_email_estudiantes — invitación a reportar
- [x] S2-10: procesar_respuestas_imap — IMAP4_SSL, lee UNSEEN
- [x] S2-11: _extraer_token_de_headers — busca respuestas+{uuid}@dominio en headers
- [x] S2-12: Guarda RespuestaDocente, marca notificacion.respondido=True
- [x] S2-13: iniciar_polling_imap — IntervalTrigger cada 15 min en scheduler
- [x] S2-14 a S2-17: crear_plantillas.py — 4 plantillas .docx con Jinja2 para informes 1-4
- [x] S2-18: doc_generator.py — generar_docx (plantilla Jinja2 o fallback básico)
- [x] S2-19: Guarda .docx en app/static/docx/ y actualiza informe.ruta_docx
- [x] S2-20: regenerar_docx — incrementa versión y regenera
- [x] S2-21: informes.py — GET /informes/{id}/descargar FileResponse
- [x] S2-22: enviar_docx_jefe — adjunta y envía .docx al jefe por correo
- [x] S2-23/24: Sprint 2 verificado y CLAUDE.md actualizado

## SPRINT 3 — COMPLETADO ✅
Objetivo: integración IA y generación completa de informes

- [x] S3-01: ia_engine.py — LiteLLM → anthropic/claude-sonnet-4-20250514
- [x] S3-02: analizar_calificaciones_interciclo — estadísticos + rangos + narrativo + acciones
- [x] S3-03: analizar_calificaciones_finales — 10 sub-análisis completos
- [x] S3-04: acciones_mejora con contexto respuesta docente (si existe)
- [x] S3-05: analizar_consolidado_area — resumen multi-asignatura + acciones generales
- [x] S3-06: Reintentos backoff exponencial (2→4→8 seg), fallback texto placeholder
- [x] S3-07: POST /informes/generar-borrador — BackgroundTask, no bloquea HTTP
- [x] S3-08: generar_informe_3 — checklist visita + calificaciones interciclo + IA + .docx
- [x] S3-09: generar_informe_4 — 10 sub-análisis IA por asig + consolidado área + .docx
- [x] S3-10: PUT /informes/{id}/secciones — ya existía, verificado
- [x] S3-11: Informe3.tsx — checklist visita 6 params + análisis interciclo IA + descarga
- [x] S3-12: Informe4.tsx — 10 sub-análisis editables + consolidado área + descarga
- [x] S3-13: Informe2.tsx — checklist AVAC 12 params + observaciones + descarga
- [x] S3-14: Informe1.tsx — 6 secciones editables + campo director + descarga
- [x] S3-15/16: Sprint 3 completado y CLAUDE.md actualizado

## SPRINT 4 — COMPLETADO ✅
Objetivo: validar con datos reales del Período 67

- [x] S4-01: seed_p67.py — 39 docentes, 44 asignaturas, 83 asignaciones P67
- [x] S4-02: Calificaciones_finales.xlsx — 75 asignaturas procesadas correctamente
- [x] S4-03: Calificaciones_interciclo.xlsx — 76 asignaturas procesadas correctamente
  - Fix importación circular: declarative.py para Base, import app.db.base en seeds y main
  - Fix excel_processor: detección exacta de columnas (GRUPO vs CODIGO_GRUPO)
  - Fix bcrypt==4.0.1 + pydantic[email] en requirements.txt
- [x] S4-04: Informe 3 (área 2, id=3) — 8 asignaturas, narrativa IA Groq completa + .docx
- [x] S4-05: Informe 4 (área 3, id=4) — 10 asignaturas, 10 sub-análisis IA completos + .docx
- [x] S4-06: Flujo emails simulado — 39 notificaciones con token Reply-To persistidas
      + recepción simulada (POST /flujo/simular-respuesta correlaciona por token).
      Fix: notificaciones ahora se guardan (informe_id nullable + consejo_id, migración 002)
- [x] S4-07: Scheduler validado — programa 2 días antes, ignora fechas pasadas,
      polling IMAP cada 15 min, restaura jobs PENDIENTE al reiniciar
- [x] S4-08: Edición secciones panel jefe — FIX: columna JSON no persistía (flag_modified)
- [x] S4-09: .docx verificado — plantillas Jinja2 generadas (crear_plantillas.py); informe 4
      sale con encabezado UPS + 10 sub-análisis + acciones + firmas (formato institucional)
- [x] S4-10: FIX calificaciones-sin-grupo — columna grupo + migración 003 + endpoint + generador.
      Validado: ÁLGEBRA conserva G21/G3/G4/G5. Tambien 2 bugs extra: BackgroundTask reusaba
      sesión DB del request (informe 4 no terminaba); dedup (asignatura,grupo) co-dictada
- [x] S4-11: Casos borde OK — parciales-en-0 (solo_nota_final), SIMULACIÓN G1 con 1 estudiante
- [x] S4-12: Permisos por rol validados — docente→director=403, sin token=401, token inválido=401
- [x] S4-13: Calidad narrativa IA verificada — análisis profesional español formal (Groq llama-3.3-70b)
- [x] S4-14: Prompts funcionan bien con datos reales; ajustes finos quedan para Sprint 5 si tutor lo pide
- [x] S4-15: CLAUDE.md Sprint 4 COMPLETADO

## SPRINTS PENDIENTES
- Sprint 5: Ajustes finales, UI, demo Taller Pitch 15-16/07/2026
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
