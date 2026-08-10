# Frontend image (Next.js 16). Builds the app and serves it with `next start`.
# The /api/* rewrite in next.config.ts proxies to the API container using
# NEXT_PUBLIC_API_URL (set to http://api:8000 in docker-compose).
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Next.js evaluates next.config.ts rewrites() at BUILD time and freezes the
# destination into the routes manifest. Setting NEXT_PUBLIC_API_URL only as a
# runtime environment variable is too late — the proxy target is already baked
# in. It must be a build argument.
#
# Default keeps `docker build` alone working for local use; compose passes
# http://api:8000 so the frontend reaches the API container over the compose
# network instead of its own loopback.
ARG NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
