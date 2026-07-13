FROM node:20-alpine AS builder

WORKDIR /appui

COPY appui/package.json appui/pnpm-lock.yaml appui/pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY appui/ ./
RUN pnpm build

FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY deploy/appui/default.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /appui/dist /usr/share/nginx/html

EXPOSE 8080
