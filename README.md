# 智炬五维协同学习系统

<div align="center">

**基于多智能体的协同学习对话平台**

[![Python](https://img.shields.io/badge/Python-3.12.7-blue)](https://www.python.org/)
[![Conda](https://img.shields.io/badge/Conda-24.11.3-green)](https://conda.io/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green)](https://nodejs.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4.0-brightgreen)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-red)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.2.0-orange)](https://langchain.com/)

</div>

---

## 📖 系统简介

智炬五维协同学习系统是一个创新的多智能体AI协同学习平台，通过模拟真实的小组讨论场景，为用户提供深度的学习和思考体验。

系统集成了多个AI模型（智谱AI、Kimi、通义千问等），通过组织者、理论家、实践者、质疑者等不同角色的智能体，进行多角度、深层次的对话讨论，帮助用户全面理解和思考问题。

---

## 💻 运行环境

本项目已在以下环境测试通过：

| 组件 | 版本 | 说明 |
|------|------|------|
| **Python** | 3.12.7 | 后端开发语言 |
| **Conda** | 24.11.3 | Python环境管理工具 |
| **Java** | 17.0.11 | 某些依赖需要Java环境 |
| **Node.js** | 18.x 或 20.x | 前端运行环境 |
| **MySQL** | 8.0+ | 数据库 |
| **LangChain** | 1.2.0 | LLM应用框架 |

---

## 📋 目录

- [快速开始](#-快速开始-docker推荐)
- [本地开发环境配置](#-本地开发环境配置)
  - [第一步：安装基础软件](#第一步安装基础软件)
  - [第二步：克隆项目](#第二步克隆项目)
  - [第三步：配置Python环境](#第三步配置python环境)
  - [第四步：安装Python依赖](#第四步安装python依赖)
  - [第五步：安装前端依赖](#第五步安装前端依赖)
  - [第六步：启动服务](#第六步启动服务)
- [依赖库详细说明](#-依赖库详细说明)
- [常见问题](#-常见问题)

---

## 🚀 快速开始（Docker推荐）

如果你已经安装了Docker和Docker Compose，这是最快速的方式：

```bash
# 1. 克隆项目
git clone https://github.com/SenAHovo/ThinkingTogether.git
cd ThinkingTogether

# 2. 启动所有服务
cd docker
docker-compose up -d

# 3. 访问应用
# 前端：http://localhost
# 后端API：http://localhost:8000
# API文档：http://localhost:8000/docs
```

**停止服务：**
```bash
docker-compose down
```

---

## 💻 本地开发环境配置

如果你想在本地进行开发或调试，请按照以下步骤配置环境。

### 第一步：安装基础软件

#### 1.1 安装Conda（Miniconda）

**Windows:**
- 访问 [https://conda.io/en/latest/miniconda.html](https://conda.io/en/latest/miniconda.html)
- 下载 Windows 64-bit Miniconda 安装器
- 运行安装程序，使用默认选项

**验证安装：**
```bash
conda --version
# 应显示：conda 24.x.x
```

#### 1.2 安装Java 17

**Windows:**
- 访问 [Oracle Java SE Downloads](https://www.oracle.com/java/technologies/downloads/)
- 下载 Java 17 (LTS) 版本
- 运行安装程序，配置环境变量 `JAVA_HOME`

**验证安装：**
```bash
java -version
# 应显示：java version "17.x.x"
```

#### 1.3 安装Node.js 18+

- 访问 [https://nodejs.org/](https://nodejs.org/)
- 下载 LTS 版本（推荐18.x或20.x）
- 运行安装程序

**验证安装：**
```bash
node --version
# 应显示：v18.x.x 或更高
npm --version
# 应显示：9.x.x 或更高
```

#### 1.4 安装MySQL 8.0+

**Windows:**
- 访问 [https://dev.mysql.com/downloads/mysql/](https://dev.mysql.com/downloads/mysql/)
- 下载 MySQL Community Server 8.0+
- 运行安装程序，设置root密码（请记住此密码）

**验证安装：**
```bash
mysql --version
# 应显示：mysql Ver 8.0.x
```

---

### 第二步：克隆项目

```bash
# 克隆项目到本地
git clone https://github.com/SenAHovo/ThinkingTogether.git
cd ThinkingTogether
```

---

### 第三步：配置Python环境

#### 3.1 创建Conda虚拟环境

```bash
# 创建名为thinking-together的虚拟环境，指定Python版本
conda create -n thinking-together python=3.12.7 -y

# 激活虚拟环境
conda activate thinking-together
```

**提示：** 激活成功后，命令行前面会显示 `(thinking-together)`

#### 3.2 验证Python版本

```bash
python --version
# 应显示：Python 3.12.7
```

---

### 第四步：安装Python依赖

#### 4.1 升级pip（推荐）

```bash
# 确保虚拟环境已激活
conda activate thinking-together

# 升级pip
python -m pip install --upgrade pip
```

#### 4.2 安装依赖

```bash
# 在项目根目录执行
pip install -r requirements.txt
```

**常见安装问题：**

- 如果安装 `pymysql` 或 `cryptography` 时报错，可能需要安装 Microsoft Visual C++ Build Tools
- Windows上如果安装 ` cryptography ` 失败：
  ```bash
  # 先安装Rust工具链
  pip install setuptools-rust
  # 然后重新安装
  pip install -r requirements.txt
  ```

#### 4.3 验证关键依赖

```bash
# 验证FastAPI
python -c "import fastapi; print(fastapi.__version__)"

# 验证LangChain
python -c "import langchain; print(langchain.__version__)"

# 验证数据库连接
python -c "import pymysql; print('pymysql OK')"
```

---

### 第五步：安装前端依赖

#### 5.1 进入前端目录

```bash
cd FrontDev
```

#### 5.2 安装依赖

```bash
npm install
```

**如果npm install很慢：**

```bash
# 使用国内镜像
npm config set registry https://registry.npmmirror.com
npm install
```

#### 5.3 返回项目根目录

```bash
cd ..
```

---

### 第六步：启动服务

#### 方式一：使用统一启动脚本（推荐）

```bash
# 确保虚拟环境已激活
conda activate thinking-together

# 运行启动脚本
python start_all.py
```

**脚本功能：**
- ✅ 自动检查并释放8000端口
- ✅ 后台启动后端服务
- ✅ 等待后端完全启动
- ✅ 启动前端开发服务器
- ✅ Ctrl+C 同时停止前后端

#### 方式二：手动分别启动

**启动后端：**
```bash
# 终端1
conda activate thinking-together
python -m uvicorn dev.api.server:app --host 0.0.0.0 --port 8000 --reload
```

**启动前端（新开一个终端）：**
```bash
# 终端2
cd FrontDev
npm run dev
```

#### 方式三：使用Docker（最简单）

```bash
cd docker
docker-compose up -d
```

---

### 访问应用

启动成功后，在浏览器中访问：

| 服务 | 本地开发地址 | Docker地址 |
|------|-------------|-----------|
| **前端界面** | http://localhost:5173 | http://localhost |
| **后端API** | http://localhost:8000 | http://localhost:8000 |
| **API文档** | http://localhost:8000/docs | http://localhost:8000/docs |

---

## 📦 依赖库详细说明

### Python后端依赖

项目所有Python依赖已列在 `requirements.txt` 文件中。

#### 核心框架

| 依赖包 | 版本要求 | 用途 |
|--------|---------|------|
| **fastapi** | >=0.104.0 | 现代化的Web框架，用于构建API |
| **uvicorn** | >=0.24.0 | ASGI服务器，用于运行FastAPI应用 |
| **pydantic** | >=2.0.0 | 数据验证和设置管理 |
| **python-dotenv** | >=1.0.0 | 从.env文件加载环境变量 |
| **python-multipart** | >=0.0.6 | 处理表单数据和文件上传 |

#### 数据库相关

| 依赖包 | 版本要求 | 用途 |
|--------|---------|------|
| **pymysql** | >=1.1.0 | MySQL数据库连接驱动 |
| **sqlalchemy** | >=2.0.0 | Python SQL工具包和ORM |
| **cryptography** | >=41.0.0 | 加密算法支持 |

#### LangChain AI框架

| 依赖包 | 版本要求 | 用途 |
|--------|---------|------|
| **langchain** | >=0.1.0 | LLM应用开发框架 |
| **langchain-openai** | >=0.0.5 | OpenAI模型集成 |
| **langchain-community** | >=0.0.10 | LangChain社区扩展 |

#### LLM提供商SDK

| 依赖包 | 版本要求 | 用途 |
|--------|---------|------|
| **openai** | >=1.0.0 | OpenAI API客户端 |
| **zhipuai** | >=2.0.0 | 智谱AI SDK |

#### 工具库

| 依赖包 | 版本要求 | 用途 |
|--------|---------|------|
| **jieba** | >=0.42.1 | 中文分词库 |
| **PyJWT** | >=2.8.0 | JWT令牌生成和验证 |
| **pyyaml** | >=6.0.1 | YAML文件解析 |
| **email-validator** | >=2.1.0 | 邮箱地址验证 |
| **httpx** | >=0.25.0 | 异步HTTP客户端 |

### 前端依赖（Node.js）

前端依赖配置在 `FrontDev/package.json` 文件中。

| 依赖包 | 版本 | 用途 |
|--------|------|------|
| **vue** | ^3.4.0 | 渐进式JavaScript框架 |
| **vite** | ^5.0.0 | 下一代前端构建工具 |
| **@vitejs/plugin-vue** | ^5.0.0 | Vue 3的Vite插件 |

---

## 🔧 常见问题

### 1. Python依赖安装失败

**问题：** `pip install` 时出现编译错误，特别是 `cryptography` 包

**解决方案：**
```bash
# 方案1：安装预编译的wheel包
pip install --only-binary :all: cryptography

# 方案2：使用conda安装 cryptography
conda install cryptography
pip install -r requirements.txt --no-deps
pip install fastapi uvicorn pydantic python-dotenv
```

### 2. MySQL连接失败

**问题：** 后端启动时提示数据库连接失败

**解决方案：**
```bash
# 检查MySQL服务是否运行
# Windows:
net start MySQL80

# 检查数据库是否存在
mysql -u root -p
SHOW DATABASES;

# 检查 .env 文件中的数据库配置是否正确
# 确保 DB_PASSWORD 与安装MySQL时设置的密码一致
```

### 3. 端口被占用

**问题：** 启动时提示8000端口已被占用

**解决方案：**
```bash
# Windows: 查找占用端口的进程
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <进程ID> /F

# 或者修改 .env 文件中的端口配置
```

### 4. 前端页面无法访问

**问题：** 后端正常运行，但前端页面打不开

**解决方案：**
```bash
# 检查Node.js版本是否符合要求（需要18+）
node --version

# 清除前端缓存重新安装
cd FrontDev
rmdir /s /q node_modules
del package-lock.json
npm install
npm run dev
```

### 5. API密钥错误

**问题：** 智能体调用失败，提示认证错误

**解决方案：**
- 检查 `.env` 文件中的API密钥是否正确
- 确认API密钥是否已激活且未过期
- 检查API密钥对应的账户是否有足够余额
- 查看后端日志 `backend_output.log` 获取详细错误信息

### 6. Java环境相关问题

**问题：** 某些依赖需要Java环境

**解决方案：**
```bash
# 验证Java版本
java -version
# 应显示 Java 17 或更高版本

# 如果版本不对，请安装 Java 17
# 设置 JAVA_HOME 环境变量指向 Java 17 安装目录
```

### 7. 虚拟环境激活失败

**问题：** Windows上 `conda activate` 命令无效

**解决方案：**
```bash
# 初始化conda（首次使用）
conda init cmd.exe

# 重启命令行窗口，然后激活
conda activate thinking-together
```

### 8. Docker相关

**问题：** 想使用Docker快速部署

**解决方案：**

如果你已将项目推送到Docker Hub，其他人可以这样使用：

```bash
# 1. 拉取镜像（请替换为你的Docker Hub用户名）
docker pull your-username/thinking-together-backend:latest
docker pull your-username/thinking-together-frontend:latest

# 2. 下载项目的 docker-compose.yml 和 .env 文件

# 3. 使用 docker-compose 启动
cd docker
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

---

## 🐳 Docker 部署指南

### 使用Docker Hub镜像（推荐给用户）

如果你已经将镜像推送到Docker Hub，用户可以按以下步骤快速部署：

#### 前提条件
- 已安装 Docker
- 已安装 Docker Compose

#### 部署步骤

**1. 创建工作目录**
```bash
mkdir thinking-together
cd thinking-together
```

**2. 下载配置文件**
从项目中获取以下文件：
- `docker-compose.yml`
- `.env`

**3. 拉取并启动容器**
```bash
# 拉取最新镜像
docker pull your-username/thinking-together:latest

# 启动服务
docker-compose up -d
```

**5. 访问应用**
- 前端界面：http://localhost
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

**6. 停止服务**
```bash
docker-compose down
```


---

## 🎯 智能体角色介绍

系统采用多智能体协同设计，每个智能体扮演不同的角色，共同完成深度讨论：

### 📋 组织者（Organizer）

- **AI模型**：智谱 GLM-4-Flash
- **职责**：
  - 引导讨论流程，确保讨论有序进行
  - 管理议程，根据讨论进展调整重点
  - 分配发言权，选择最合适的智能体发言
  - 总结讨论成果，提炼关键观点
- **特点**：客观、理性、统筹全局

### 🎓 理论家（Theorist）

- **AI模型**：智谱 GLM-4-Flash
- **职责**：
  - 建立理论框架，提供概念基础
  - 进行概念辨析，澄清模糊术语
  - 提供结构化的分析和分类
  - 探讨问题的本质和深层含义
- **特点**：学术派、严谨、重视边界条件
- **风格**：谨慎克制，喜欢讲清楚前提和判断标准

### 🔧 实践者（Practitioner）

- **AI模型**：Kimi moonshot-v1-8k
- **职责**：
  - 提供具体的实际案例
  - 给出可执行的建议和行动方案
  - 将理论联系实际应用
  - 分享实战经验和最佳实践
- **特点**：接地气、务实、注重可操作性
- **风格**：像朋友聊天，用场景和具体动作推进讨论

### ❓ 质疑者（Skeptic）

- **AI模型**：通义千问 qwen-plus
- **职责**：
  - 提出质疑，验证讨论的前提假设
  - 指出逻辑漏洞和论证不充分之处
  - 提供反例和反面思考
  - 促使讨论更加严谨和全面
- **特点**：犀利但友善，专抓偷换概念和证据不足
- **风格**：逼大家把前提说清楚，避免得出不可靠的结论

### 🤝 协同机制

四个智能体通过以下方式协同工作：

1. **组织者开场**：理解用户话题，制定讨论议程
2. **动态路由**：组织者根据讨论进展，智能选择下一位发言者
3. **角色互补**：理论、实践、质疑三种视角相互补充
4. **持续迭代**：每个智能体发言后，组织者更新讨论状态
5. **用户参与**：用户可以随时插话，影响讨论走向

---

## 📂 项目结构

```
ThinkingTogether/
├── dev/                          # 后端核心代码
│   ├── agents/                   # 智能体模块
│   │   ├── organizer_agent.py    # 组织者智能体
│   │   ├── theorist_tool.py      # 理论家工具
│   │   ├── practitioner_tool.py  # 实践者工具
│   │   ├── skeptic_tool.py       # 质疑者工具
│   │   ├── rewriter_tools.py     # 内容重写工具
│   │   └── model_client.py       # AI模型客户端
│   ├── api/                      # API服务层
│   │   └── server.py             # FastAPI服务器
│   ├── auth/                     # 认证模块
│   │   └── auth_utils.py         # JWT认证工具
│   ├── email/                    # 邮件服务
│   │   ├── email_service.py      # 邮件发送
│   │   └── verification.py       # 验证码服务
│   ├── memory/                   # 记忆管理
│   │   ├── history_store.py      # 对话历史存储
│   │   └── state_store.py        # 讨论状态管理
│   ├── mysql/                    # 数据库模块
│   │   ├── db_config.py          # 数据库配置
│   │   ├── db_utils.py           # 数据库工具
│   │   ├── persistent_store.py   # 持久化存储
│   │   ├── content_analyzer.py   # 内容分析
│   │   └── main_with_db.py       # 数据库主程序
│   └── main.py                   # 命令行入口
│
├── FrontDev/                     # 前端代码
│   ├── src/
│   │   ├── App.vue               # 主应用组件
│   │   ├── api.js                # API调用封装
│   │   ├── main.js               # 应用入口
│   │   └── assets/               # 静态资源
│   ├── public/                   # 公共资源
│   ├── index.html                # HTML模板
│   ├── vite.config.js            # Vite配置
│   └── package.json              # 前端依赖配置
│
├── docker/                       # Docker 配置
│   ├── docker-compose.yml        # Docker Compose 配置
│   ├── Dockerfile                # 后端 Dockerfile
│   ├── FrontDev.Dockerfile       # 前端 Dockerfile
│   ├── nginx.conf                # Nginx 配置
│   ├── push-to-dockerhub.bat     # 推送到Docker Hub脚本
│   ├── tk.sql                    # 数据库初始化脚本
│   └── release-package/          # 发布包
│
├── utils/                        # 工具函数
│   ├── agent_utils.py            # 智能体工具
│   ├── companion_tool_io.py      # 智能体IO工具
│   └── content_analyzer.py       # 内容分析工具
│
├── .env                          # 环境变量配置
├── .gitignore                    # Git忽略文件
├── start_all.py                  # 统一启动脚本
├── requirements.txt              # Python依赖清单
├── tk.sql                        # 数据库初始化脚本
├── README.md                     # 本文件
└── DOCKER_GUIDE.md               # Docker 完整指南
```

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户界面层                          │
│                   (Vue 3 + Vite)                       │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/REST API
                       ▼
┌─────────────────────────────────────────────────────────┐
│                     API服务层                           │
│                   (FastAPI + Uvicorn)                   │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│  认证模块     │ │ 智能体层  │ │  记忆管理     │
│  (JWT)       │ │(LangChain)│ │ (状态存储)    │
└──────────────┘ └─────┬────┘ └──────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│  智谱AI      │ │  Kimi    │ │  通义千问     │
│  (GLM-4)     │ │(Moonshot)│ │   (Qwen)     │
└──────────────┘ └──────────┘ └──────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    数据持久化层                         │
│              (MySQL 8.0 + SQLAlchemy)                   │
└─────────────────────────────────────────────────────────┘
```


<div align="center">

**⭐ 如果这个项目对你有帮助，请给它一个星标！**

**💡 有问题或建议？欢迎提 Issue 或 PR！**

Made with ❤️ by Thinking Together Team

</div>
