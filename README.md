# 智炬五维协同学习系统

<div align="center">

**一个基于多智能体协作的AI驱动协同学习平台**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4.0-green)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-red)](https://fastapi.tiangolo.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0%2B-orange)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 项目简介

**智炬五维**（Thinking Together）是一个创新的多智能体协作学习平台，通过模拟真实小组讨论场景，让用户与四个不同角色的AI智能体进行结构化对话，实现深度学习和知识建构。

### 核心特点

- 🤖 **多智能体协作**：理论家、实践者、质疑者、组织者各司其职
- 💬 **结构化讨论**：开场 → 讨论 → 收尾的完整流程
- 💾 **持久化存储**：所有对话历史和状态保存在MySQL数据库
- 🔐 **用户认证体系**：注册、登录、邮箱验证完整流程
- 🌐 **实时通信**：WebSocket实时对话流
- 🔍 **内容管理**：对话公开分享、评论互动、内容审核
- 🛡️ **违禁词过滤**：基于Trie树的高效敏感词检测

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户界面层 (Vue 3)                    │
├─────────────────────────────────────────────────────────┤
│                    API服务层 (FastAPI)                   │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ 组织者   │  │ 理论家   │  │ 实践者   │  │ 质疑者   │ │
│  │ (智谱)   │  │ (GPT)    │  │ (Kimi)   │  │ (千问)   │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
├─────────────────────────────────────────────────────────┤
│              数据持久化层 (MySQL 8.0+)                   │
└─────────────────────────────────────────────────────────┘
```

---

## 功能模块

### 用户功能

- ✅ 用户注册/登录（邮箱验证）
- ✅ 创建和管理对话
- ✅ 与AI智能体实时对话
- ✅ 导出对话记录（TXT/ZIP）
- ✅ 公开对话大厅浏览
- ✅ 点赞和评论互动

### 管理员功能

- ✅ 用户管理（创建、编辑、删除、封禁）
- ✅ 内容审核（公开请求审核）
- ✅ 评论管理（查看、删除、恢复）
- ✅ 违禁词管理（添加、编辑、删除、启用/禁用）
- ✅ 数据看板（用户、对话、评论统计）

### AI智能体

| 角色 | 模型 | 特点 |
|-----|------|------|
| 🎙️ 组织者 | 智谱GLM-4 | 流程控制、路由调度、总结收尾 |
| 📚 理论家 | GPT系列 | 概念分析、理论框架、边界澄清 |
| 🔧 实践者 | Kimi | 场景落地、实操建议、约束分析 |
| 🔍 质疑者 | 通义千问 | 逻辑检验、风险评估、观点平衡 |

---

## 快速开始

### 环境要求

- **Python**: 3.9+
- **Node.js**: 16.x 或 18.x
- **MySQL**: 8.0+
- **操作系统**: Windows / macOS / Linux

### 1. 克隆项目

```bash
git clone https://github.com/your-username/thinking-together.git
cd thinking-together
```

### 2. 配置Python环境

```bash
# 创建虚拟环境
conda create -n thinking-together python=3.9
conda activate thinking-together

# 安装依赖
pip install fastapi uvicorn pyjwt pymysql pydantic python-dotenv
pip install langchain langchain-openai langchain-community
```

### 3. 配置数据库

```bash
# 创建数据库
mysql -u root -p
CREATE DATABASE thinking_together CHARACTER SET utf8mb4;

# 导入表结构
mysql -u root -p thinking_together < thinking_together.sql
```

### 4. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# 数据库配置
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=thinking_together

# JWT密钥
JWT_SECRET_KEY=your-secret-key

# 邮件配置
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SENDER_EMAIL=your_email@qq.com
SENDER_AUTH_CODE=your_auth_code

# LLM API配置
ZHIPU_API_KEY=your_zhipu_api_key
ZHIPU_MODEL_NAME=glm-4
API_KEY=your_openai_api_key
BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4
```

### 5. 启动后端

```bash
python start_backend.py
```

后端将运行在 `http://localhost:8000`

### 6. 启动前端

```bash
python start_frontend.py
```

前端将运行在 `http://localhost:5173`

### 7. 访问系统

- **用户界面**: http://localhost:5173/
- **管理后台**: http://localhost:5173/#admin
- **API文档**: http://localhost:8000/docs

---

## 目录结构

```
thinking-togetherMaster/
├── dev/                     # 后端核心模块
│   ├── agents/             # AI智能体
│   │   ├── organizer_agent.py      # 组织者
│   │   ├── theorist_tool.py        # 理论家
│   │   ├── practitioner_tool.py    # 实践者
│   │   ├── skeptic_tool.py         # 质疑者
│   │   └── model_client.py         # LLM模型客户端
│   ├── api/                # FastAPI服务器
│   │   └── server.py       # API主入口
│   ├── auth/               # 用户认证
│   │   └── auth_utils.py   # JWT工具
│   ├── email/              # 邮件服务
│   │   ├── email_service.py
│   │   └── verification.py
│   ├── memory/             # 记忆和状态管理
│   │   ├── history_store.py
│   │   └── state_store.py
│   ├── mysql/              # 数据库模块
│   │   ├── db_config.py
│   │   ├── db_utils.py
│   │   └── persistent_store.py
│   └── main.py             # 命令行入口
├── FrontDev/               # 前端项目
│   ├── src/
│   │   ├── App.vue         # 主应用
│   │   ├── Admin.vue       # 管理后台
│   │   ├── PublicChats.vue # 公开大厅
│   │   ├── api.js          # API客户端
│   │   └── main.js         # 入口文件
│   ├── package.json
│   └── vite.config.js
├── database/               # 数据库脚本
│   └── schema.sql
├── utils/                  # 工具模块
├── start_backend.py        # 后端启动脚本
├── start_frontend.py       # 前端启动脚本
├── thinking_together.sql   # 完整数据库导出
├── .env                    # 环境变量配置
└── README.md
```

---

## 技术栈

### 后端

- **Web框架**: FastAPI
- **数据库**: MySQL 8.0+ (PyMySQL)
- **认证**: JWT (PyJWT)
- **LLM框架**: LangChain
- **模型提供商**:
  - 智谱AI (组织者)
  - OpenAI (理论家)
  - Moonshot AI (实践者)
  - 阿里云 (质疑者)

### 前端

- **框架**: Vue 3.4.0
- **构建工具**: Vite 5.0.0
- **HTTP客户端**: Fetch API
- **实时通信**: WebSocket

---

## 数据库设计

### 核心表

- **threads**: 讨论线程
- **events**: 发言事件
- **agenda**: 议程项目
- **consensus**: 共识点
- **disagreements**: 分歧点
- **open_questions**: 开放问题

### 用户表

- **users**: 用户信息
- **user_sessions**: 用户会话
- **email_verification_codes**: 邮箱验证码

### 内容表

- **comments**: 评论
- **thread_likes**: 点赞
- **thread_owners**: 对话所有者

### 管理表

- **forbidden_words**: 违禁词
- **moderation_logs**: 审核日志

---

## API文档

系统使用FastAPI自动生成交互式API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要API端点

| 端点 | 方法 | 描述 |
|-----|------|------|
| `/api/chats` | POST | 创建新对话 |
| `/api/chats` | GET | 获取对话列表 |
| `/api/messages` | POST | 发送消息 |
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/login` | POST | 用户登录 |
| `/ws/chat/{chatId}` | WebSocket | 实时通信 |

---

## 常见问题

### 1. 数据库连接失败

检查MySQL服务是否运行：
```bash
# Windows
tasklist | findstr mysql

# Linux/macOS
sudo systemctl status mysql
```

### 2. 端口被占用

```bash
# 查看8000端口占用
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <进程ID> /F
```

### 3. LLM API调用失败

- 检查 `.env` 文件中的API Key是否正确
- 检查网络连接
- 检查API额度

### 4. 邮件发送失败

- QQ邮箱需使用授权码而非登录密码
- 授权码获取：QQ邮箱 → 设置 → 账户 → POP3/SMTP服务

---

## 项目特色

### 1. 多智能体协作

四个不同角色的AI智能体协同工作，各自发挥专长：

- **组织者**：智能路由，动态调度讨论流程
- **理论家**：深度分析，构建理论框架
- **实践者**：落地场景，提供实操建议
- **质疑者**：逻辑检验，识别潜在风险

### 2. 内容质量控制

- 反模板检测和自动重写
- 风格健康度统计
- 上下文窗口优化

### 3. 高性能违禁词过滤

基于Trie树算法，实现O(n×k)时间复杂度的实时检测：

```python
# 插入违禁词
trie.insert("敏感词", category="政治", severity=3)

# 搜索违禁词
result = trie.search("用户评论内容")
```

### 4. 完善的管理系统

- 用户管理和权限控制
- 内容审核流程
- 违禁词动态管理
- 数据可视化看板

---

## 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交Pull Request

---

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 联系方式

- **作者**: Thinking Together Team
- **邮箱**: contact@example.com
- **官网**: https://example.com

---

## 致谢

感谢以下开源项目的支持：

- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [LangChain](https://langchain.com/)
- [Vite](https://vitejs.dev/)

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给一个Star！ ⭐**

Made with ❤️ by Thinking Together Team

</div>
