# 智炬五维协同学习系统

<div align="center">

**基于多智能体的协同学习对话平台**

[![Python](https://img.shields.io/badge/Python-3.12.7-blue)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-17+-green)](https://nodejs.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4.0-brightgreen)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-red)](https://fastapi.tiangolo.com/)

</div>

---

## 💻 运行环境

| 组件 | 版本要求 | 说明 |
|------|---------|------|
| **Python** | 3.8+ | 后端开发语言 |
| **Conda** | 24.x+ | Python环境管理工具 |
| **Node.js** | 17+ | 前端运行环境 |
| **MySQL** | 8.0+ | 数据库 |
| **LangChain** | 1.2.0+ | LLM应用框架 |

---

## 📦 依赖库及安装

### 后端依赖（Python）

**安装命令：**

```bash
pip install -r requirements.txt
```

**核心依赖清单：**

```txt
# 核心框架
fastapi>=0.104.0              # Web框架
uvicorn[standard]>=0.24.0     # ASGI服务器
pydantic>=2.0.0               # 数据验证
python-dotenv>=1.0.0          # 环境变量管理
python-multipart>=0.0.6       # 表单数据处理

# 数据库
pymysql>=1.1.0                # MySQL连接
sqlalchemy>=2.0.0             # ORM框架

# LangChain AI框架
langchain>=0.1.0              # AI框架
langchain-openai>=0.0.5       # OpenAI集成
langchain-community>=0.0.10   # LangChain社区组件

# LLM提供商SDK
openai>=1.0.0                 # OpenAI API客户端
zhipuai>=2.0.0                # 智谱AI SDK

# 工具库
jieba>=0.42.1                 # 中文分词
PyJWT>=2.8.0                  # JWT认证
pyyaml>=6.0.1                 # YAML文件处理
email-validator>=2.1.0        # 邮箱验证
httpx>=0.25.0                 # HTTP客户端
```

### 前端依赖（Node.js）

```bash
cd FrontDev
npm install
```

**核心依赖：**
- `vue@^3.4.0` - 前端框架
- `vite@^5.0.0` - 构建工具
- `@vitejs/plugin-vue@^5.0.0` - Vue插件

---

## 🐳 使用 Docker（推荐）

### 快速启动

```bash
cd docker
docker-compose up -d
```

访问：http://localhost

### 停止服务

```bash
docker-compose down
```

### Docker 文档

- **[Docker 完整指南](DOCKER_GUIDE.md)** - 详细的 Docker 操作说明
- **[快速参考](docker/QUICK_REF.md)** - 常用命令速查表

### 推送到 Docker Hub

```bash
cd docker
push-to-dockerhub.bat
```

---

## 🚀 本地开发运行步骤

### 第一步：准备 Python 环境

```bash
# 使用 Conda 创建虚拟环境
conda create -n thinking-together python=3.12.7
conda activate thinking-together
```

### 第二步：安装依赖

```bash
# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd FrontDev
npm install
cd ..
```

### 第三步：配置环境变量

在项目根目录创建 `.env` 文件



### 第四步：启动服务

**使用统一启动脚本（推荐）：**

```bash
python start_all.py
```

启动脚本会自动：
- ✅ 检查并释放8000端口
- ✅ 启动后端服务（后台运行）
- ✅ 等待后端完全启动
- ✅ 启动前端服务
- ✅ Ctrl+C 同时停止前后端

### 第五步：访问应用

#### Docker 方式

| 服务 | 地址 |
|------|------|
| **前端界面** | http://localhost |
| **后端API** | http://localhost:8000 |
| **API文档** | http://localhost:8000/docs |
| **MySQL** | localhost:3306 |

#### 本地开发方式

| 服务 | 地址 |
|------|------|
| **前端界面** | http://localhost:5173 |
| **后端API** | http://localhost:8000 |
| **API文档** | http://localhost:8000/docs |

---

## 🎯 智能体角色介绍

### 📋 组织者（Organizer）

- **职责**：引导讨论流程、管理议程、分配发言权
- **AI模型**：智谱 GLM-4-Flash

### 🎓 理论家（Theorist）

- **职责**：建立理论框架、概念辨析、结构化分析
- **AI模型**：智谱 GLM-4-Flash

### 🔧 实践者（Practitioner）

- **职责**：提供具体案例、可执行建议、联系实际应用
- **AI模型**：Kimi moonshot-v1-8k

### ❓ 质疑者（Skeptic）

- **职责**：提出质疑、验证前提、指出逻辑漏洞
- **AI模型**：通义千问 qwen-plus

---

## 📂 项目结构

```
thinking-togetherMaster/
├── dev/                          # 后端核心代码
│   ├── agents/                   # 智能体模块
│   ├── api/                      # API服务
│   ├── auth/                     # 认证模块
│   ├── email/                    # 邮件服务
│   ├── memory/                   # 记忆管理
│   └── mysql/                    # 数据库模块
│
├── FrontDev/                     # 前端代码
│   └── src/
│       ├── App.vue               # 主应用组件
│       ├── api.js                # API调用封装
│       └── main.js               # 入口文件
│
├── docker/                       # Docker 配置
│   ├── docker-compose.yml        # Docker Compose 配置
│   ├── Dockerfile                # 后端 Dockerfile
│   ├── FrontDev.Dockerfile       # 前端 Dockerfile
│   ├── nginx.conf                # Nginx 配置
│   ├── push-to-dockerhub.bat     # 推送脚本
│   └── QUICK_REF.md              # 快速参考
│
├── .env                          # 环境变量配置
├── .env.example                  # 配置模板
├── start_all.py                  # 统一启动脚本
├── requirements.txt              # Python依赖
├── DOCKER_GUIDE.md               # Docker 完整指南
└── README.md                     # 本文件
```



<div align="center">

**⭐ 如果这个项目对你有帮助，请给它一个星标！**

Made with ❤️ by Thinking Together Team

</div>
