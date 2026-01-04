# Docker 容器管理指南

智炬五维协同学习系统 - Docker 完整操作指南

---

## 目录

1. [修改代码后重新打包](#1-修改代码后重新打包)
2. [本地服务管理](#2-本地服务管理)
3. [推送到 Docker Hub](#3-推送到-docker-hub)
4. [他人如何使用您的容器](#4-他人如何使用您的容器)
5. [常见问题排查](#5-常见问题排查)

---

## 1. 修改代码后重新打包

### 1.1 修改前端代码

如果修改了 `FrontDev/` 目录下的前端代码：

```bash
cd docker
docker-compose build frontend
```

### 1.2 修改后端代码

如果修改了 `dev/` 目录下的后端代码：

```bash
cd docker
docker-compose build backend
```

### 1.3 同时修改前后端代码

```bash
cd docker
docker-compose build
```

### 1.4 修改配置文件

如果修改了以下配置文件，需要重新构建相应服务：
- `requirements.txt` → 重新构建 backend
- `FrontDev/package.json` → 重新构建 frontend
- `docker/Dockerfile` 或 `docker/FrontDev.Dockerfile` → 重新构建对应服务

### 1.5 清理旧镜像（可选，节省空间）

```bash
# 删除悬空镜像
docker image prune -f

# 删除所有旧镜像（谨慎使用）
docker images | grep thinking-together | awk '{print $3}' | xargs docker rmi -f
```

---

## 2. 本地服务管理

### 2.1 启动所有服务

```bash
cd docker
docker-compose up -d
```

**参数说明：**
- `-d`: 后台运行（detached mode）

### 2.2 查看服务状态

```bash
cd docker
docker-compose ps
```

### 2.3 查看服务日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mysql

# 查看最后 100 行日志
docker-compose logs --tail=100 backend
```

**参数说明：**
- `-f`: 实时跟踪日志（follow）
- `--tail=N`: 显示最后 N 行

### 2.4 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
docker-compose restart frontend
```

### 2.5 停止服务

```bash
# 停止所有服务（保留容器）
docker-compose stop

# 停止特定服务
docker-compose stop backend
```

### 2.6 停止并删除容器

```bash
# 停止并删除所有容器
docker-compose down

# 停止并删除所有容器、网络、卷
docker-compose down -v

# 停止并删除所有容器、网络、卷、镜像
docker-compose down -v --rmi all
```

### 2.7 进入容器调试

```bash
# 进入后端容器
docker exec -it thinking-together-backend sh

# 进入前端容器
docker exec -it thinking-together-frontend sh

# 进入 MySQL 容器
docker exec -it thinking-together-mysql mysql -uroot -p
```

---

## 3. 推送到 Docker Hub

### 3.1 重新打标签

每次重新构建后，需要重新打标签：

```bash
# 标签后端镜像
docker tag docker-backend:latest senaho/thinking-together-backend:latest

# 标签前端镜像
docker tag docker-frontend:latest senaho/thinking-together-frontend:latest
```

### 3.2 使用版本标签（推荐）

建议使用版本号而不是 `latest`：

```bash
# 假设版本为 v1.0.1
docker tag docker-backend:latest senaho/thinking-together-backend:v1.0.1
docker tag docker-frontend:latest senaho/thinking-together-frontend:v1.0.1
```

### 3.3 登录 Docker Hub

```bash
docker login --username senaho
```

输入密码后登录。

### 3.4 推送镜像

```bash
# 推送 latest 标签
docker push senaho/thinking-together-backend:latest
docker push senaho/thinking-together-frontend:latest

# 推送版本标签
docker push senaho/thinking-together-backend:v1.0.1
docker push senaho/thinking-together-frontend:v1.0.1
```

### 3.5 使用自动化脚本（推荐）

```bash
cd docker
push-to-dockerhub.bat
```

**注意：** 每次修改脚本中的版本号（如果使用版本标签的话）

### 3.6 推送前检查清单

- [ ] 已重新构建镜像（`docker-compose build`）
- [ ] 已重新打标签（`docker tag`）
- [ ] 已登录 Docker Hub（`docker login`）
- [ ] 镜像名称正确（`senaho/thinking-together-*`）

---

## 4. 他人如何使用您的容器

### 4.1 准备工作文档

创建 `README.md` 或分享以下内容：

---

### **智炬五维协同学习系统 - Docker 部署指南**

#### 前置要求

- Docker 已安装（版本 20.10+）
- Docker Compose 已安装
- 端口 80、8000、3306 未被占用

#### 快速启动

**1. 拉取镜像**

```bash
docker pull senaho/thinking-together-backend:latest
docker pull senaho/thinking-together-frontend:latest
```

**2. 创建 docker-compose.yml**

创建以下内容的 `docker-compose.yml` 文件：

```yaml
services:
  # MySQL 数据库
  mysql:
    image: mysql:8.0
    container_name: thinking-together-mysql
    environment:
      MYSQL_ROOT_PASSWORD: your_password
      MYSQL_DATABASE: tk
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - thinking-network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      timeout: 20s
      retries: 10

  # 后端服务
  backend:
    image: senaho/thinking-together-backend:latest
    container_name: thinking-together-backend
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=mysql
      - DB_USER=root
      - DB_PASSWORD=your_password
      - DB_NAME=tk
      - DB_PORT=3306
    depends_on:
      mysql:
        condition: service_healthy
    networks:
      - thinking-network
    volumes:
      - ./logs:/app/logs

  # 前端服务
  frontend:
    image: senaho/thinking-together-frontend:latest
    container_name: thinking-together-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - thinking-network

networks:
  thinking-network:
    driver: bridge

volumes:
  mysql_data:
```

**3. 启动服务**

```bash
docker-compose up -d
```

**4. 访问应用**

- 前端：http://localhost
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

**5. 查看日志**

```bash
docker-compose logs -f
```

**6. 停止服务**

```bash
docker-compose down
```

#### 配置说明

根据您的实际需求，修改以下配置：
- `MYSQL_ROOT_PASSWORD`: MySQL root 密码
- `MYSQL_DATABASE`: 数据库名称
- 端口映射（如果需要避免冲突）

#### 故障排查

```bash
# 查看服务状态
docker-compose ps

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend
docker-compose logs mysql

# 重启服务
docker-compose restart
```

---

### 4.2 为不同环境提供配置

#### 开发环境配置

```yaml
# docker-compose.dev.yml
services:
  backend:
    environment:
      - DEBUG=true
    volumes:
      - ./dev:/app/dev  # 挂载本地代码目录
```

#### 生产环境配置

```yaml
# docker-compose.prod.yml
services:
  frontend:
    ports:
      - "443:443"  # 使用 HTTPS
    # 添加 SSL 证书配置
```

### 4.3 提供环境变量模板

创建 `.env.example` 文件：

```bash
# 数据库配置
DB_HOST=mysql
DB_USER=root
DB_PASSWORD=your_secure_password
DB_NAME=tk
DB_PORT=3306

# API 密钥（根据需要配置）
ZHIPU_API_KEY=your_zhipu_api_key
KM_API_KEY=your_kimi_api_key
QWEN_API_KEY=your_qwen_api_key
```

---

## 5. 常见问题排查

### 5.1 端口被占用

**错误信息：**
```
bind: address already in use
```

**解决方案：**
```bash
# Windows 查看端口占用
netstat -ano | findstr ":80"
netstat -ano | findstr ":8000"
netstat -ano | findstr ":3306"

# 停止占用端口的进程
taskkill /PID <进程ID> /F

# 或修改 docker-compose.yml 中的端口映射
ports:
  - "8080:80"  # 使用其他端口
```

### 5.2 容器启动失败

**排查步骤：**

```bash
# 1. 查看容器状态
docker-compose ps

# 2. 查看详细日志
docker-compose logs backend

# 3. 检查配置文件
cat docker/.env

# 4. 验证镜像是否存在
docker images | grep thinking-together
```

### 5.3 数据库连接失败

**检查项：**

```bash
# 1. 验证 MySQL 是否健康
docker exec thinking-together-mysql mysqladmin ping -h localhost -uroot -p

# 2. 检查网络连接
docker network inspect docker_thinking-network

# 3. 查看后端环境变量
docker exec thinking-together-backend env | grep DB_
```

### 5.4 前端无法访问后端

**检查 nginx 配置：**

```bash
# 查看 nginx 配置
docker exec thinking-together-frontend cat /etc/nginx/conf.d/default.conf

# 重启前端容器
docker-compose restart frontend
```

### 5.5 镜像推送失败

**常见原因：**

1. **未登录**
```bash
docker login --username senaho
```

2. **镜像名称错误**
```bash
# 必须是您的用户名开头
senaho/thinking-together-backend:latest  # ✓ 正确
thinking-together-backend:latest         # ✗ 错误
```

3. **网络问题**
```bash
# 使用代理（如果需要）
export HTTP_PROXY=http://your-proxy:port
docker push senaho/thinking-together-backend:latest
```

### 5.6 清理 Docker 空间

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的卷
docker volume prune

# 清理未使用的网络
docker network prune

# 一键清理所有（谨慎使用）
docker system prune -a --volumes
```

---

## 6. 完整工作流示例

### 场景：修改了后端代码并发布新版本

```bash
# 1. 修改代码
# ... 编辑 dev/api/*.py ...

# 2. 重新构建
cd docker
docker-compose build backend

# 3. 本地测试
docker-compose up -d
docker-compose logs -f backend

# 4. 确认无误后，打标签
docker tag docker-backend:latest senaho/thinking-together-backend:v1.0.2
docker tag docker-backend:latest senaho/thinking-together-backend:latest

# 5. 推送到 Docker Hub
docker login --username senaho
docker push senaho/thinking-together-backend:v1.0.2
docker push senaho/thinking-together-backend:latest

# 6. 通知使用者更新
# "新版本 v1.0.2 已发布，请运行：docker pull senaho/thinking-together-backend:v1.0.2"
```

---

## 7. 参考命令速查表

```bash
# === 构建相关 ===
docker-compose build              # 构建所有服务
docker-compose build backend      # 仅构建后端
docker-compose build frontend     # 仅构建前端

# === 服务管理 ===
docker-compose up -d              # 启动所有服务
docker-compose ps                 # 查看状态
docker-compose logs -f            # 查看日志
docker-compose restart            # 重启服务
docker-compose stop               # 停止服务
docker-compose down               # 停止并删除容器

# === 镜像管理 ===
docker images                     # 列出镜像
docker tag <源镜像> <目标镜像>    # 重新打标签
docker push <镜像名>              # 推送到 Docker Hub
docker pull <镜像名>              # 从 Docker Hub 拉取

# === 清理 ===
docker system prune -f            # 清理未使用资源
docker image prune -f             # 清理未使用镜像
docker volume prune -f            # 清理未使用卷

# === 调试 ===
docker exec -it <容器名> sh       # 进入容器
docker logs <容器名>              # 查看容器日志
docker inspect <容器名>           # 查看容器详细信息
```

---

## 8. 附录

### 8.1 Docker Hub 镜像地址

- 后端：https://hub.docker.com/r/senaho/thinking-together-backend
- 前端：https://hub.docker.com/r/senaho/thinking-together-frontend

### 8.2 项目结构

```
thinking-togetherMaster/
├── dev/                    # 后端源代码
├── FrontDev/              # 前端源代码
├── docker/
│   ├── docker-compose.yml # Docker Compose 配置
│   ├── Dockerfile         # 后端 Dockerfile
│   ├── FrontDev.Dockerfile # 前端 Dockerfile
│   ├── nginx.conf         # Nginx 配置
│   ├── .env               # 环境变量
│   └── push-to-dockerhub.bat # 推送脚本
└── DOCKER_GUIDE.md        # 本文档
```

### 8.3 支持与反馈

如有问题，请查看：
- Docker 官方文档：https://docs.docker.com/
- Docker Compose 文档：https://docs.docker.com/compose/

---

**文档版本：** v1.0
**最后更新：** 2026-01-04
**维护者：** senaho
