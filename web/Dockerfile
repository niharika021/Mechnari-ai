# Mechnari.ai frontend - deployed to Cloud Run as its own service.
#
# NEXT_PUBLIC_API_BASE is baked into the client bundle at build time (that
# is how Next.js env vars work), so it has to be supplied as a build arg
# pointing at the *already-deployed* API service's URL - deploy api first.

# ---- deps: install once, cached across builds that don't touch package*.json
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- builder: compile with the real API URL inlined
FROM node:20-slim AS builder
WORKDIR /app
# Every NEXT_PUBLIC_* value has to be present at build time - Next.js
# inlines them into the client bundle, so setting them at run time does
# nothing. Unset Firebase values simply hide the sign-in button; the app
# works signed out.
ARG NEXT_PUBLIC_API_BASE
ARG NEXT_PUBLIC_FIREBASE_API_KEY
ARG NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
ARG NEXT_PUBLIC_FIREBASE_PROJECT_ID
ARG NEXT_PUBLIC_FIREBASE_APP_ID
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
ENV NEXT_PUBLIC_FIREBASE_API_KEY=${NEXT_PUBLIC_FIREBASE_API_KEY}
ENV NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=${NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN}
ENV NEXT_PUBLIC_FIREBASE_PROJECT_ID=${NEXT_PUBLIC_FIREBASE_PROJECT_ID}
ENV NEXT_PUBLIC_FIREBASE_APP_ID=${NEXT_PUBLIC_FIREBASE_APP_ID}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---- runner: just the standalone server, no dev dependencies
FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
# CopilotKit's runtime reports usage telemetry to its vendor unless told
# not to. Off by default here - this app's premise is proprietary warranty
# data, so nothing about its use should leave the deployment.
ENV COPILOTKIT_TELEMETRY_DISABLED=true
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Cloud Run injects PORT; Next.js's standalone server reads it directly.
ENV PORT=8080
EXPOSE 8080
CMD ["node", "server.js"]
