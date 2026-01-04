# 构建阶段
FROM node:18-alpine as builder

WORKDIR /app

# 复制整个 FrontDev 目录
COPY FrontDev/ ./

# 安装依赖
RUN npm install

# 安装 dos2unix 并转换 node_modules/.bin 中所有脚本的换行符
RUN apk add --no-cache dos2unix && \
    find node_modules/.bin -type f -exec dos2unix {} \; && \
    npm run build

# 生产阶段
FROM nginx:alpine

# 复制构建产物到 nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置（从 docker 目录）
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
