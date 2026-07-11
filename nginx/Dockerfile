# Imagen web de producción: compila el frontend y lo sirve con nginx,
# que además hace de reverse proxy hacia la API.
#
# En desarrollo se usa el servidor de Vite (recarga en caliente). Ese servidor NO
# debe exponerse en producción: no está optimizado ni endurecido.
#
# El contexto de build es la raíz del repositorio (ver docker-compose.prod.yml).

# ── 1. Compilar el frontend ───────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Con el lockfile, para que el build sea reproducible
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build          # genera /app/dist

# ── 2. Servir ─────────────────────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/nginx.prod.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
