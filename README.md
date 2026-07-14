# Sistema de Informes Académicos — UPS Cuenca

Sistema web para **automatizar la generación de los cuatro informes de seguimiento
académico** de la Carrera de Computación de la Universidad Politécnica Salesiana
(Sede Cuenca), requeridos por el proceso de acreditación **CACES**.

El sistema centraliza la configuración académica (períodos, consejos, áreas,
asignaturas, docentes), procesa las calificaciones desde archivos Excel, y genera
los informes en formato Word (.docx) con narrativa asistida por IA y formato
institucional (logo, encabezado y pie de página).

---

## Tabla de contenidos
1. [Arquitectura del sistema](#arquitectura-del-sistema)
2. [Stack tecnológico](#stack-tecnológico)
3. [Requisitos](#requisitos)
4. [Guía de implementación](#guía-de-implementación)
5. [Variables de entorno](#variables-de-entorno)
6. [Modo prueba de correo](#modo-prueba-de-correo)
7. [Fechas de entrega y recordatorios automáticos](#fechas-de-entrega-y-recordatorios-automáticos)
8. [URLs y credenciales](#urls-y-credenciales)
9. [Modelo de roles](#modelo-de-roles)
10. [Los cuatro informes](#los-cuatro-informes)
11. [Estructura del proyecto](#estructura-del-proyecto)
12. [Despliegue en producción](#despliegue-en-producción)
13. [Comandos útiles](#comandos-útiles)

---

## Arquitectura del sistema

El sistema corre completamente en contenedores Docker orquestados con Docker Compose.
Nginx actúa como único punto de entrada (reverse proxy) hacia el frontend y la API.

```
                          ┌─────────────────────────────────────────────┐
                          │                  NAVEGADOR                    │
                          └───────────────────────┬─────────────────────┘
                                                  │  http://localhost
                                                  ▼
                          ┌─────────────────────────────────────────────┐
                          │              NGINX (reverse proxy)            │
                          │   /            → frontend (SPA React)         │
                          │   /api/v1/...  → backend (FastAPI)            │
                          │   /docs        → OpenAPI (Swagger)            │
                          └──────────┬──────────────────────┬───────────┘
                                     │                      │
                     ┌───────────────▼──────┐   ┌───────────▼────────────────┐
                     │   FRONTEND (Vite)    │   │      BACKEND (FastAPI)      │
                     │  React + TypeScript  │   │  ┌───────────────────────┐ │
                     │  Tailwind CSS        │   │  │ API REST /api/v1       │ │
                     │  React Router        │   │  │ Auth JWT + bcrypt      │ │
                     │  Axios (JWT + refresh)│  │  │ Rol efectivo por       │ │
                     └──────────────────────┘   │  │   jefatura activa      │ │
                                                 │  ├───────────────────────┤ │
                                                 │  │ SERVICIOS              │ │
                                                 │  │ • excel_processor      │ │
                                                 │  │ • ia_engine (LiteLLM)  │ │
                                                 │  │ • generador_informes   │ │
                                                 │  │ • doc_generator (docx) │ │
                                                 │  │ • mail_service (SMTP)  │ │
                                                 │  │ • scheduler (APSch.)   │ │
                                                 │  └───────────────────────┘ │
                                                 └───────┬─────────────┬──────┘
                                                         │             │
                                        ┌────────────────▼──┐   ┌──────▼───────────┐
                                        │   PostgreSQL 15    │   │  Proveedor IA     │
                                        │  (SQLAlchemy +     │   │  (GROQ vía        │
                                        │   Alembic)         │   │   LiteLLM)        │
                                        └────────────────────┘   └───────────────────┘
```

### Flujo funcional

1. **Configuración (Director):** crea períodos, consejos de carrera, áreas
   curriculares, asignaturas y usuarios; asigna docentes a asignaturas/grupos y
   designa jefes de área.
2. **Carga de calificaciones (Director):** sube el Excel de calificaciones
   (interciclo o finales). `excel_processor` detecta columnas automáticamente,
   filtra por área y estructura los datos con estadísticos.
3. **Generación de informes (Jefe de Área / Director):** el sistema arma el
   borrador. Para los informes con análisis (3 y 4), `ia_engine` genera la
   narrativa profesional en español; `doc_generator` produce el `.docx` con
   formato institucional a partir de plantillas Jinja2.
4. **Notificaciones automáticas (Scheduler):** APScheduler programa el envío de
   correos a docentes/estudiantes 2 días antes de la fecha límite del consejo.
   Los docentes registran sus observaciones y acciones de mejora desde su panel.
5. **Revisión y descarga:** los informes se previsualizan (render del `.docx`
   real en el navegador) y se descargan.

### Componentes del backend

| Servicio | Responsabilidad |
|----------|-----------------|
| `excel_processor.py` | Lee Excel, detecta columnas (sinónimos), filtra por área, calcula estadísticos |
| `ia_engine.py` | Genera análisis narrativo vía LiteLLM (GROQ); reintentos con backoff y fallback |
| `generador_informes.py` | Orquesta la construcción del contenido de cada informe (1–4) |
| `doc_generator.py` | Renderiza plantillas Jinja2 `.docx` con el contenido; formato institucional |
| `mail_service.py` | Envío SMTP de correos con el logo institucional embebido |
| `scheduler.py` | Jobs de APScheduler (envío programado de recordatorios), zona America/Guayaquil |

---

## Stack tecnológico

| Capa | Tecnologías |
|------|-------------|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, React Router v6, Axios, lucide-react, docx-preview |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy, Alembic, Pydantic v2, APScheduler, pandas/openpyxl |
| **Documentos** | python-docx-template (Jinja2 en `.docx`), python-docx |
| **IA** | LiteLLM (multi-proveedor: GROQ por defecto; soporta DeepSeek, Gemini, Anthropic) |
| **Base de datos** | PostgreSQL 15 |
| **Infraestructura** | Docker, Docker Compose, Nginx (reverse proxy) |
| **Seguridad** | JWT (python-jose) + bcrypt (passlib), auto-refresh de token en el frontend |

---

## Requisitos

- **Docker Desktop 24+**
- **Docker Compose v2+**
- **Git**

> No se requiere instalar Node.js ni Python en el host: todo corre dentro de contenedores.

---

## Guía de implementación

```bash
# 1. Clonar el repositorio
git clone https://github.com/f4b14n144/Proyecto-Titulacion.git
cd Proyecto-Titulacion

# 2. Crear el archivo de variables de entorno y completarlo
cp .env.example .env
#    Editar .env con las credenciales reales (ver sección Variables de entorno)

# 3. Levantar todos los servicios (postgres + backend + frontend + nginx)
docker compose up --build -d

# 4. Aplicar las migraciones de base de datos
docker compose exec backend alembic upgrade head

# 5. Cargar datos iniciales (roles, director, áreas curriculares)
docker compose exec backend python -m app.db.seed

# 6. Generar las plantillas .docx base (Jinja2) — REQUERIDO para el formato institucional
docker compose exec backend python app/static/plantillas/crear_plantillas.py

# 7. (Opcional) Datos reales del Período 67 para pruebas
docker compose exec backend python -m app.db.seed_p67

# 8. (Opcional) Cuentas de prueba por rol (director / jefe de área / docente)
docker compose exec backend python -m app.db.seed_test_users
```

Al terminar, el sistema queda disponible en **http://localhost**.

### Atajo: dejar el sistema listo para una demostración

Los pasos 5, 7 y 8 (y algunos más) se pueden ejecutar de una sola vez. El comando
es **idempotente**: se puede repetir sin duplicar datos.

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python app/static/plantillas/crear_plantillas.py
docker compose exec backend python -m app.db.seed_demo
```

`seed_demo` carga las áreas, el período 67 con sus 44 asignaturas y 39 docentes,
asigna las 6 jefaturas de área a docentes reales, crea las cuentas de prueba y al
terminar **imprime con qué credenciales entrar**.

No carga calificaciones: los `.xlsx` contienen datos reales de estudiantes y no
están en el repositorio. Para cargarlas, entra como directora y usa
*Subir Calificaciones*.

> **Nota sobre las plantillas `.docx`:** se generan con el script del paso 6 y **no
> se versionan en el repo**. Sin ellas, los informes salen con un formato básico de
> respaldo en lugar del formato institucional completo (logo, encabezado y pie).

> **Nota sobre el proveedor de IA:** por defecto se usa **GROQ** (free tier, sin
> tarjeta). Requiere `GROQ_API_KEY` en `.env`. El motor soporta otros proveedores
> cambiando `AI_PROVIDER` y `AI_MODEL`.

---

## Variables de entorno

Copiar `.env.example` a `.env` y completar:

```env
# Base de datos
DATABASE_URL=postgresql://usuario:password@postgres:5432/informes_db

# Seguridad (generar con: openssl rand -hex 32)
SECRET_KEY=<clave secreta>

# Proveedor de IA (por defecto GROQ)
AI_PROVIDER=groq
AI_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=<api key de GROQ>

# Correo saliente (envío de notificaciones y recordatorios)
SMTP_HOST=<host SMTP>
SMTP_PORT=587
SMTP_USER=<cuenta de correo>
SMTP_PASSWORD=<clave / app password>

# Interruptor global de correo (ver más abajo)
MAIL_MODO_PRUEBA=true
MAIL_REDIRECT_TO=<tu correo, para recibir todo mientras pruebas>
```

> `.env` está en `.gitignore` y **nunca** debe subirse al repositorio.

---

## Modo prueba de correo

El sistema envía correos a docentes y estudiantes, algunos de forma **automática**
(el planificador avisa 2 días antes de cada entrega). Para no escribirle a nadie
real mientras se prueba, hay un interruptor global en el `.env`:

| `MAIL_MODO_PRUEBA` | `MAIL_REDIRECT_TO` | Qué ocurre |
|---|---|---|
| `true` | `tu@correo.com` | **Todos** los correos llegan a esa dirección. El destinatario original va en el asunto: `[PRUEBA · para docente@ups.edu.ec] …` |
| `true` | *(vacío)* | **No se envía nada.** Solo se registra en el log. |
| `false` | — | **Envío real.** Los correos llegan a docentes y estudiantes. |

El interruptor se aplica **dentro del servicio de correo**, en la capa más baja. Eso
es deliberado: todos los correos del sistema pasan por ahí, así que **ningún camino
puede saltárselo** — ni los envíos manuales desde la interfaz, ni los automáticos
del planificador. Un interruptor que viviera solo en la interfaz dejaría al
planificador enviando correos reales sin que nadie se lo pidiera.

Al arrancar, el backend deja claro en qué modo está:

```
CORREO EN MODO PRUEBA — todo se redirige a: tu@correo.com
CORREO EN MODO REAL — los correos llegan a sus destinatarios
```

> **En producción va en `false`.** Si se deja en `true`, el backend lo avisa como un
> problema de configuración al arrancar.

> **Ojo:** `docker compose restart` **no relee el `.env`**. Tras cambiarlo hay que
> recrear el contenedor: `docker compose up -d --force-recreate backend`.

---

## Fechas de entrega y recordatorios automáticos

Cada Consejo de Carrera tiene **una fecha de entrega por informe** (1, 2, 3 y 4). Las
fija la Dirección de Carrera desde *Consejos de Carrera* → **Fechas de entrega**.

**Dos días antes** de cada fecha, el planificador envía un recordatorio:

- A los **jefes de área**, que elaboran el informe. El texto detalla qué les toca
  hacer según el informe (p. ej. para el 2: completar el checklist del aula virtual).
- A los **docentes**, para que registren sus observaciones y acciones de mejora antes
  de que el informe se cierre. Un solo correo por docente, listando sus materias.

Los recordatorios se reprograman al arrancar el servidor, de modo que **sobreviven a
un reinicio**. Una fecha que ya pasó no se programa.

---

## URLs y credenciales

### URLs

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost |
| API | http://localhost/api/v1 |
| Documentación API (Swagger) | http://localhost/docs |
| Backend directo | http://localhost:8000 |
| Frontend directo (dev) | http://localhost:5173 |

### Credenciales por defecto (solo desarrollo)

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| director@ups.edu.ec | director123 | Director de Carrera |
| jefe@ups.edu.ec | pass123 | Docente + jefatura → opera como Jefe de Área |
| docente@ups.edu.ec | pass123 | Docente |

> **Cambiar las contraseñas inmediatamente en producción.**

---

## Modelo de roles

El sistema distingue **rol base** y **rol efectivo**:

- **Rol base:** el de todo profesor es `DOCENTE`. Solo el director tiene
  `DIRECTOR_CARRERA` como rol base.
- **Rol efectivo:** es el rol con el que la persona **opera realmente**:
  - `DIRECTOR_CARRERA` → siempre, si su rol base lo es.
  - `JEFE_AREA` → si tiene una **jefatura asignada en el período activo**.
  - `DOCENTE` → en cualquier otro caso.

Así, asignar o quitar la jefatura de un docente cambia automáticamente el panel al
que accede y cómo aparece en el sistema, sin necesidad de editar su rol base.

---

## Los cuatro informes

| # | Informe | Contenido |
|---|---------|-----------|
| **1** | Centro Docente | Formulario del consejo de carrera: agenda, designaciones de jefes de área (auto-llenado), observaciones curriculares, encuestas, resoluciones. Autoría del director. |
| **2** | Revisión AVAC | Checklist de 12 parámetros del aula virtual por docente/asignatura + análisis de cumplimiento del área. |
| **3** | Visitas Áulicas e Interciclo | Checklist de visitas áulicas + análisis de calificaciones de interciclo (Parcial 1) con narrativa IA. |
| **4** | Análisis Final | 10 sub-análisis con IA por asignatura (distribución, parciales, recuperación, outliers, patrones) + consolidado del área. |

Los informes 2, 3 y 4 se generan **por área**; el informe 1 es a nivel de carrera.

---

## Estructura del proyecto

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          Routers y endpoints REST
│   │   ├── core/            Configuración, seguridad (JWT), dependencias, rol efectivo
│   │   ├── db/              Sesión, base declarativa, seeds
│   │   ├── models/          Modelos SQLAlchemy (un archivo por tabla)
│   │   ├── schemas/         Esquemas Pydantic v2
│   │   ├── services/        excel_processor, ia_engine, generador_informes,
│   │   │                    doc_generator, mail_service, scheduler
│   │   └── static/
│   │       └── plantillas/  Script que genera las plantillas .docx (Jinja2)
│   └── alembic/             Migraciones de base de datos
│
├── frontend/
│   ├── public/              Recursos estáticos (logo)
│   └── src/
│       ├── components/      Navbar, Sidebar, ProtectedRoute
│       ├── hooks/           useAuth (contexto de autenticación)
│       ├── pages/           Login, panel director/*, panel jefe_area/*
│       ├── services/        api (Axios), auth, informes
│       └── types/           Interfaces TypeScript
│
├── nginx/                   Configuración del reverse proxy
├── docker-compose.yml       Orquestación de servicios
├── .env.example             Plantilla de variables de entorno
└── README.md
```

---

## Despliegue en producción

El `docker-compose.yml` de la raíz es para **desarrollo**: corre el servidor de Vite
con recarga en caliente, publica los puertos de la base de datos y del backend, y
expone la documentación de la API. **No debe usarse en producción.**

Para producción existe `docker-compose.prod.yml`:

```bash
# 1. Preparar el .env de producción
cp .env.example .env
#    - SECRET_KEY: obligatorio, generar con `openssl rand -hex 32`
#    - POSTGRES_PASSWORD: una contraseña fuerte (no "password")
#    - ENVIRONMENT=production
#    - CORS_ORIGINS: el dominio real (https://informes.ups.edu.ec)
#    - SMTP_*: una cuenta institucional, no personal

# 2. Levantar
docker compose -f docker-compose.prod.yml up -d --build

# 3. Migraciones, plantillas y datos iniciales
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python app/static/plantillas/crear_plantillas.py
docker compose -f docker-compose.prod.yml exec backend python -m app.db.seed
```

### Checklist antes de salir a producción

- [ ] `SECRET_KEY` generada con `openssl rand -hex 32`.
      *Con la de ejemplo se pueden falsificar tokens de cualquier usuario; el backend
      se niega a arrancar.*
- [ ] `POSTGRES_PASSWORD` fuerte (no `password`).
- [ ] `ENVIRONMENT=production` — oculta `/docs` y `/redoc`.
- [ ] `CORS_ORIGINS` con el dominio real, no `localhost`.
- [ ] **`MAIL_MODO_PRUEBA=false`** — si queda en `true`, los correos no llegan a
      nadie. El backend lo avisa al arrancar.
- [ ] `SMTP_*` de una cuenta **institucional**, no personal.
      *Gmail limita los envíos diarios y una tanda son ~90 correos.*
- [ ] `GROQ_API_KEY` (o la del proveedor de IA que se use).
- [ ] Cambiar la contraseña de la cuenta de dirección tras el primer acceso.

### Qué cambia respecto a desarrollo

| | Desarrollo | Producción |
|---|---|---|
| Frontend | Servidor de Vite (`npm run dev`) | **Build estático** servido por nginx |
| Puertos publicados | 80, 8000 (API), 5173 (Vite), 5432 (BD) | **Solo el 80** |
| `/docs` y `/redoc` | Visibles | **404** |
| Descarga de `.docx` | — | Solo por la API, con JWT |
| Backend | `--reload` | Sin reload, 1 worker |
| Correo | `MAIL_MODO_PRUEBA=true` | `false` (envío real) |
| Secretos | Valores por defecto | **Obligatorios**: el backend no arranca con una `SECRET_KEY` de ejemplo |

> **Un solo worker, a propósito.** El planificador (APScheduler) va embebido en
> FastAPI. Con varios workers arrancaría una vez por worker y los correos
> programados se enviarían duplicados. Para escalar habría que sacar el
> planificador a un proceso aparte.

> **Los informes nunca se sirven como archivos estáticos.** Contienen notas de
> estudiantes; se descargan por `GET /api/v1/informes/{id}/descargar`, que valida el
> JWT y el rol del usuario.

---

## Comandos útiles

```bash
# Ver logs del backend en vivo
docker compose logs -f backend

# Acceder a una shell del backend
docker compose exec backend bash

# Crear una nueva migración (autogenerada desde los modelos)
docker compose exec backend alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones pendientes
docker compose exec backend alembic upgrade head

# Regenerar las plantillas .docx tras cambiar su formato
docker compose exec backend python app/static/plantillas/crear_plantillas.py

# Detener todos los servicios
docker compose down

# Detener y borrar volúmenes (reinicio limpio de la base de datos)
docker compose down -v
```
