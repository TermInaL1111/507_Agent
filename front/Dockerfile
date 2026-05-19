FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_AMAP_KEY
ARG VITE_AMAP_SECURITY_CODE
ENV VITE_AMAP_KEY=$VITE_AMAP_KEY
ENV VITE_AMAP_SECURITY_CODE=$VITE_AMAP_SECURITY_CODE

COPY package*.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN apk add --no-cache openssl \
    && mkdir -p /etc/nginx/certs \
    && openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -keyout /etc/nginx/certs/selfsigned.key \
        -out /etc/nginx/certs/selfsigned.crt \
        -subj "/CN=8.137.19.10" \
        -addext "subjectAltName=IP:8.137.19.10,DNS:localhost"

EXPOSE 80 443
