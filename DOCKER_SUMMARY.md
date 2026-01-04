# Docker 部署完整指南

## 📁 目录结构

```
thinking-togetherMaster/
└── docker/                          ⭐ Docker 部署包
    ├── 构建文件                      （用于构建镜像）
    │   ├── Dockerfile               - 后端镜像定义
    │   ├── FrontDev.Dockerfile      - 前端镜像定义
    │   ├── FrontDev.dockerignore    - 前端构建排除
    │   ├── .dockerignore            - 后端构建排除
    │   ├── nginx.conf               - Nginx 配置
    │   ├── docker-compose.yml       - 本地构建和测试
    │   ├── tk.sql                   - 数据库初始化文件
    │   ├── push-images.bat          - 一键推送脚本
    │   └── test-docker.bat          - 本地测试脚本
    │
    └── release-package/             （分享给用户的发布包）
        ├── docker-compose.yml       - 引用 Docker Hub 镜像
        ├── .env                     - 环境变量（包含默认配置）
        ├── tk.sql                   - 数据库文件
        └── README.md                - 使用说明
```

---

## 🎯 完整部署流程

### 第一步：本地测试

#### 方式1：使用测试脚本（推荐）

```bash
# 进入 docker 目录
cd docker

# 双击运行测试脚本
test-docker.bat
```

#### 方式2：手动执行

```bash
cd docker

# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 访问测试
# 浏览器打开：http://localhost:8000/docs

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 第二步：推送到 Docker Hub

#### 1. 编辑推送脚本

```bash
cd docker
notepad push-images.bat
```

修改第 11 行的用户名：
```batch
set USERNAME=yourusername
```

#### 2. 运行推送脚本

```bash
# 双击运行
push-images.bat
```

或手动执行：
```bash
# 登录
docker login

# 标记镜像（替换 yourusername）
docker tag thinking-together-master-backend senaho/thinking-together-backend:v1.0
docker tag thinking-together-master-frontend yourusername/thinking-together-frontend:v1.0

# 推送
docker push yourusername/thinking-together-backend:v1.0
docker push yourusername/thinking-together-frontend:v1.0
```

### 第三步：修改发布包配置

```bash
cd docker/release-package
notepad docker-compose.yml
```

找到第 30 行和第 49 行，修改镜像名称：

```yaml
# 修改前
image: yourusername/thinking-together-backend:v1.0
image: yourusername/thinking-together-frontend:v1.0

# 修改后（替换为你的用户名）
image: 你的用户名/thinking-together-backend:v1.0
image: 你的用户名/thinking-together-frontend:v1.0
```

### 第四步：打包和分享

#### 方式1：压缩包

```bash
# 在 Windows 资源管理器中
# 右键点击 docker/release-package 文件夹
# 发送到 -> 压缩(zipped)文件夹
```

#### 方式2：GitHub 仓库（推荐）

```bash
cd docker/release-package
git init
git add .
git commit -m "Docker deployment package"
git remote add origin https://github.com/yourusername/thinking-together-docker.git
git push -u origin main
```

---

## 📦 用户使用流程

### 对方只需要：

1. **下载4个文件**（从 `docker/release-package/`）
   - docker-compose.yml
   - .env
   - tk.sql
   - README.md

2. **放到同一目录**

3. **一键启动**
   ```bash
   docker-compose up -d
   ```

4. **访问应用**
   - 前端：http://localhost
   - 后端：http://localhost:8000
   - API文档：http://localhost:8000/docs

---

## 📊 文件说明

### docker 目录文件

| 文件 | 说明 |
|------|------|
| `Dockerfile` | 后端 Python 镜像定义 |
| `FrontDev.Dockerfile` | 前端 Vue 镜像定义 |
| `nginx.conf` | Nginx 配置文件 |
| `.dockerignore` | 后端构建排除文件 |
| `FrontDev.dockerignore` | 前端构建排除文件 |
| `docker-compose.yml` | 本地构建配置 |
| `tk.sql` | 数据库初始化脚本 |
| `push-images.bat` | 一键推送脚本 |
| `test-docker.bat` | 本地测试脚本 |

### docker/release-package 文件

| 文件 | 说明 |
|------|------|
| `docker-compose.yml` | 引用 Docker Hub 镜像的配置 |
| `.env` | 环境变量（包含所有默认配置） |
| `tk.sql` | 数据库初始化文件 |
| `README.md` | 用户使用说明 |

---

## ⚠️ 重要提示

### 1. 修改用户名

在以下 3 个地方将 `yourusername` 替换为你的 Docker Hub 用户名：

1. `docker/push-images.bat` 第 11 行
2. `docker/release-package/docker-compose.yml` 第 30 行
3. `docker/release-package/docker-compose.yml` 第 49 行

### 2. 测试要点

本地测试时检查：
- [ ] 所有容器正常启动（3个容器）
- [ ] 数据库初始化成功（15个表）
- [ ] 后端 API 可访问
- [ ] 前端页面可加载
- [ ] WebSocket 连接正常
- [ ] 可以正常登录

### 3. 数据库说明

- 首次启动自动执行 `tk.sql`
- 包含 15 个数据表结构
- 包含 3 个测试用户：
  - admin / 123456
  - user / 123456
  - spadmin / admin123

---

## 🔧 常用命令

### 本地测试

```bash
cd docker

# 构建
docker-compose build

# 启动
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止
docker-compose stop

# 删除容器
docker-compose down

# 删除容器和数据卷
docker-compose down -v
```

### 镜像操作

```bash
# 标记
docker tag <source> <target>

# 推送
docker push <image_name>

# 拉取
docker pull <image_name>

# 查看
docker images
```

---

## 🎉 完成检查清单

### 推送前：
- [ ] Docker 已启动
- [ ] 已登录 Docker Hub
- [ ] 已修改 `push-images.bat` 中的用户名
- [ ] 已运行 `test-docker.bat` 测试
- [ ] 所有服务运行正常

### 推送后：
- [ ] 镜像推送成功
- [ ] 在 Docker Hub 看到两个镜像
- [ ] 已修改 `release-package/docker-compose.yml`
- [ ] 已在新目录测试发布包
- [ ] 发布包可以正常启动

---

## 📞 遇到问题？

### 常见问题解决

**1. 推送失败**
```bash
# 重新登录
docker login
# 检查网络
# 确认用户名正确
```

**2. 容器启动失败**
```bash
# 查看日志
docker-compose logs

# 删除重试
docker-compose down -v
docker-compose up -d
```

**3. 数据库初始化失败**
```bash
# 查看初始化日志
docker-compose logs mysql | grep init

# 手动导入
docker exec -it thinking-together-mysql mysql -u root -p thinking_together < /docker-entrypoint-initdb.d/init.sql
```

**4. 构建失败 - commit failed / no such file or directory**

这是 Docker Desktop 的缓存问题，解决步骤：

```bash
cd docker

# 方式1：使用清理脚本（推荐）
cleanup-docker.bat

# 方式2：手动清理
# 清理构建缓存
docker builder prune -f

# 清理系统缓存
docker system prune -a --volumes -f

# 然后重启 Docker Desktop：
# 1. 关闭 Docker Desktop
# 2. 等待 10 秒
# 3. 重新打开 Docker Desktop
# 4. 等待 Docker 完全启动（看到 Docker is running）
# 5. 重新构建：docker-compose build
```

如果问题仍然存在：

```bash
# 完全清理 Docker（谨慎！会删除所有数据）
docker system prune -a --volumes --force

# 然后重启 Docker Desktop
```

---

## 📝 快速参考

### 核心命令速查

```bash
# 进入 docker 目录
cd docker

# 本地测试
test-docker.bat

# 推送镜像
push-images.bat

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 完全清理
docker-compose down -v
```

---

**祝部署顺利！** 🚀

完成所有步骤后，分享 `docker/release-package/` 目录中的 4 个文件给其他人，他们就可以一键运行你的系统了！
