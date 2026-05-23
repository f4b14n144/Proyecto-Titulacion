# Pendientes y Preguntas Abiertas

## Preguntas para Fabian — responder antes de Sprint 2

1. **Dominio email institucional**: ¿Cuál es el dominio real para `REPLY_TO_DOMAIN`?
   (ej: `ups.edu.ec`) — necesario para los tokens Reply-To de docentes.

2. **Credenciales Brevo**: ¿Ya tienes cuenta Brevo con SMTP_USER y SMTP_PASSWORD?
   Free tier: 300 emails/día — suficiente para desarrollo.

3. **IMAP para respuestas**: ¿Habrá un buzón IMAP dedicado para recibir respuestas
   de docentes? (ej: respuestas@ups.edu.ec)

4. **API Key Anthropic**: ¿Ya tienes la API key para las pruebas de IA (Sprint 3)?
   Colocarla en `.env` → `ANTHROPIC_API_KEY=sk-ant-...`

5. **Datos reales P67**: ¿Tienes disponibles estos archivos para Sprint 4?
   - Horario-P67.xlsx (docentes, asignaturas, áreas, grupos)
   - Calificaciones_finales.xlsx
   - Calificaciones_hasta_el_interciclo.xlsx

6. **VPS producción**: ¿Ya está contratado el Hetzner CX22? ¿IP disponible?
   (necesario para Sprint 5 — despliegue y SSL)

7. **Nombre del período activo**: ¿Qué nombre tendrá el período para datos de ejemplo?
   (usando "2026-1" por defecto en seed.py hasta confirmación)

## Preguntas para Sprint 1 (pueden resolverse durante el sprint)

8. **Áreas reales**: Las 5 áreas en seed.py son genéricas. ¿Cuáles son las áreas
   reales de la Carrera de Computación UPS para reemplazarlas?

9. **Asignaturas reales**: ¿Hay un listado de asignaturas y códigos para cargar
   en seed.py o preferimos crearlas desde el panel?

## Bloqueantes activos
- Ninguno para Sprint 1.

## Notas técnicas
- El archivo `.env` tiene valores de desarrollo (no sensibles). Fabian debe
  completar las credenciales reales de Brevo, IMAP y Anthropic cuando estén disponibles.
- La contraseña de admin es `admin1234` solo para desarrollo — cambiar en producción.
