# AD Password Reset Application

[English](README.md) | 中文

一个基于 Web 的 Active Directory 用户密码重置应用程序，支持邮箱验证和安全的密码重置流程。

## 功能特性

- 🔐 安全的 AD 密码重置
- 📧 邮箱验证码验证
- 🛡️ 完整的审计日志
- 🚀 现代化的 React 界面
- 📱 响应式设计（移动端 + 桌面端）
- 🔒 多层安全防护（CSRF、速率限制、LDAP 注入防护）

## 技术栈

- **后端**: Python Flask
- **前端**: React + TypeScript + Vite
- **目录服务**: LDAP/Active Directory
- **邮件服务**: SMTP
- **日志**: Python logging

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 18+（仅开发前端时需要）
- Active Directory 环境
- SMTP 邮件服务

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd AD_PassWord_Reset
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填写实际配置
   ```

5. **运行应用**
   ```bash
   python run.py
   ```

应用将在 **http://localhost:5001** 启动。

## 前端开发

如需修改前端界面：

```bash
cd frontend
npm install
npm run dev      # 开发模式
npm run build    # 构建生产版本
```

## 环境配置

### 必需的环境变量

复制 `.env.example` 为 `.env` 并配置以下变量：

#### LDAP 配置
| 变量 | 说明 |
|-----|-----|
| `LDAP_SERVER` | AD 服务器地址 |
| `LDAP_PORT` | LDAP 端口 (636/389) |
| `LDAP_BASE_DN` | AD 基础 DN |
| `LDAP_DOMAIN` | AD 域名 |
| `LDAP_USER` | 管理员账号 |
| `LDAP_PASSWORD` | 管理员密码 |

#### SMTP 配置
| 变量 | 说明 |
|-----|-----|
| `SMTP_SERVER` | 邮件服务器地址 |
| `SMTP_PORT` | SMTP 端口 (465/587) |
| `SMTP_USERNAME` | 发件人邮箱 |
| `SMTP_PASSWORD` | 邮箱密码 |

#### 应用配置
| 变量 | 说明 |
|-----|-----|
| `SERVER_IP` | 服务器 IP 地址 |
| `SECRET_KEY` | Flask 密钥（使用强随机值） |
| `FLASK_ENV` | 运行环境 (development/production) |

## 安全注意事项

⚠️ **重要**: 
- 确保 `.env` 文件不会被提交到版本控制系统
- 在生产环境中使用强密码和安全的密钥
- 定期检查审计日志 (`logs/audit.log`)
- 确保 LDAP 连接使用 SSL 加密

## 项目结构

```
AD_PassWord_Reset/
├── backend/                # 后端代码
│   ├── app.py             # Flask 应用主文件
│   ├── config.py          # 配置管理
│   ├── routes/            # API 路由
│   ├── services/          # 业务逻辑
│   └── utils/             # 工具函数
├── frontend/              # React 前端
│   ├── src/               # 源代码
│   ├── dist/              # 构建产物
│   └── package.json       # 前端依赖
├── logs/                  # 日志文件
├── .env.example           # 环境变量模板
├── requirements.txt       # Python 依赖
└── run.py                 # 应用启动文件
```

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
