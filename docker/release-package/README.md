# 智炬五维协同学习系统 - Docker 快速部署

基于多智能体的协同学习对话平台

---

## 📦 系统要求

- Docker 20.10+
- Docker Compose 2.0+

检查版本：
```bash
docker --version
docker-compose --version
```

---

## 🚀 快速开始

### 第一步：检查文件

确保当前目录包含以下文件：

```bash
dir
# 应该看到：
# docker-compose.yml
# .env                  （已包含默认配置）
# tk.sql                （数据库初始化文件）
# README.md
```

### 第二步：启动服务

```bash
# 拉取镜像并启动
docker-compose up -d

# 查看启动状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

**配置说明：**
- `.env` 文件已包含默认配置，可以直接使用
- 如需修改API密钥，编辑 `.env` 文件
- 首次启动会自动导入 `tk.sql` 初始化数据库

### 第三步：访问应用

| 服务 | 地址 | 说明 |
|------|------|------|
| **前端界面** | http://localhost | 主应用 |
| **后端API** | http://localhost:8000 | API服务 |
| **API文档** | http://localhost:8000/docs | Swagger文档 |

---

## 🔧 常用命令

```bash
# 停止服务
docker-compose stop

# 启动服务
docker-compose start

# 重启服务
docker-compose restart

# 停止并删除容器
docker-compose down

# 停止并删除容器及数据卷（⚠️ 会删除数据库数据）
docker-compose down -v

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mysql

# 进入容器
docker exec -it thinking-together-backend bash
docker exec -it thinking-together-mysql mysql -u root -p
```

---

## 📊 镜像信息

- **后端镜像**：`yourusername/thinking-together-backend:v1.0`
  - Python 3.12.7
  - FastAPI + LangChain

- **前端镜像**：`yourusername/thinking-together-frontend:v1.0`
  - Vue 3 + Nginx
  - 生产环境优化

---

## 🗂️ 数据持久化

MySQL 数据存储在 Docker Volume 中：

```bash
# 查看数据卷
docker volume ls

# 备份数据
docker run --rm -v thinking-together-mysql_data:/data \
  -v %cd%:/backup alpine tar czf /backup/mysql-backup.tar.gz /data

# 恢复数据
docker run --rm -v thinking-together-mysql_data:/data \
  -v %cd%:/backup alpine tar xzf /backup/mysql-backup.tar.gz -C /
```

### 数据库表结构

系统包含以下主要数据表：

| 表名 | 说明 |
|------|------|
| `users` | 用户表（账户、权限、认证） |
| `threads` | 讨论线程表（对话会话） |
| `thread_owners` | 对话所有者表（公开状态、审核） |
| `events` | 发言事件表（对话内容） |
| `agenda_items` | 议程项目表（讨论焦点） |
| `user_sessions` | 用户会话表（Token管理） |
| `thread_likes` | 对话点赞表 |
| `comments` | 对话评论表 |
| `email_verification_codes` | 邮箱验证码表 |
| `forbidden_words` | 违禁词表 |
| `moderation_logs` | 审核日志表 |
| `consensus` | 共识点表 |
| `disagreements` | 争议点表 |
| `open_questions` | 开放问题表 |
| `style_health` | 风格健康统计表 |

**初始数据：**
- 默认管理员账户：`admin` / `123456`
- 测试用户：`user` / `123456`
- 超级管理员：`spadmin` / `admin123`

---

## 🔍 故障排查

### 问题1：容器无法启动

```bash
# 查看详细日志
docker-compose logs backend

# 检查环境变量
docker-compose config
```

### 问题2：数据库连接失败

```bash
# 检查 MySQL 是否启动
docker exec thinking-together-mysql mysqladmin ping

# 检查数据库是否已初始化
docker exec thinking-together-mysql mysql -u root -p${DB_PASSWORD} -e "SHOW TABLES;"

# 查看 MySQL 初始化日志
docker-compose logs mysql | grep "init"
```

**首次启动说明：**
- 首次启动时，MySQL 会自动执行 `tk.sql` 初始化数据库
- 如果初始化失败，删除数据卷后重试：
  ```bash
  docker-compose down -v
  docker-compose up -d
  ```

### 问题3：数据库表不存在

如果提示表不存在，手动导入数据库：

```bash
# 1. 确认 tk.sql 文件在当前目录
dir tk.sql

# 2. 复制 SQL 文件到容器
docker cp tk.sql thinking-together-mysql:/tmp/init.sql

# 3. 进入容器并导入
docker exec -it thinking-together-mysql bash
mysql -u root -p${DB_PASSWORD} ${DB_NAME} < /tmp/init.sql
exit

# 4. 重启后端服务
docker-compose restart backend
```

### 问题4：API 返回错误

```bash
# 检查后端日志
docker-compose logs backend

# 测试 API 连接
curl http://localhost:8000/docs
```

### 问题5：端口冲突

如果 80、8000、3306 端口被占用，修改 `docker-compose.yml`：

```yaml
services:
  frontend:
    ports:
      - "8080:80"  # 改为其他端口

  backend:
    ports:
      - "8888:8000"  # 改为其他端口

  mysql:
    ports:
      - "33306:3306"  # 改为其他端口
```

---

## 📝 升级镜像

```bash
# 拉取最新镜像
docker-compose pull

# 重新创建容器
docker-compose up -d --force-recreate
```

---

## 🛡️ 安全建议

1. **生产环境部署**
   - 修改默认密码
   - 使用强密码策略
   - 配置防火墙规则
   - 定期备份数据

2. **API 密钥管理**
   - 不要将 `.env` 文件提交到版本控制
   - 定期更换 API 密钥
   - 使用密钥管理服务（如 Docker Secrets）

---

## 📞 技术支持

- 📖 项目文档：查看完整项目 README
- 🐛 问题反馈：提交 Issue
- 💬 讨论交流：加入讨论组

---

## 📄 许可证

MIT License

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给它一个星标！**

Made with ❤️ by Thinking Together Team

</div>
