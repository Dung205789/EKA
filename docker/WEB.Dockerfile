FROM node:20-alpine AS builder
WORKDIR /app/web

COPY web/package.json ./package.json
RUN npm install --no-audit --no-fund

COPY web ./
# Ensure /app/web/public exists even if repo has no public/
RUN mkdir -p public
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app/web
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Standalone output
COPY --from=builder /app/web/.next/standalone ./
COPY --from=builder /app/web/.next/static ./.next/static
COPY --from=builder /app/web/public ./public

EXPOSE 3000

# Server-only env for proxying to FastAPI
ENV EKA_API_URL=http://api:8000

CMD ["node", "server.js"]
