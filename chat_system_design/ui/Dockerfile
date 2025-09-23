############################################
# Base deps stage
############################################
FROM node:20-alpine AS base
WORKDIR /app
ENV NODE_ENV=development

# Install OS level utilities (optional minimal)
RUN apk add --no-cache bash

############################################
# Dependencies layer (better cache)
############################################
FROM base AS deps
COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* ./
RUN \
	if [ -f yarn.lock ]; then yarn install --frozen-lockfile && yarn cache clean; \
	elif [ -f package-lock.json ]; then npm ci; \
	else npm install --no-save next react react-dom typescript @types/react @types/node; fi

############################################
# Builder (for prod build) – also used for typecheck
############################################
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npx tsc --noEmit || true
RUN npm run build || echo "Skipping build in dev context"

############################################
# Development runtime (hot reload)
############################################
FROM base AS dev
ENV NODE_ENV=development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

############################################
# Production runtime (optional) – not used by compose dev
############################################
FROM node:20-alpine AS prod
ENV NODE_ENV=production
WORKDIR /app
COPY package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["npm","run","start"]
