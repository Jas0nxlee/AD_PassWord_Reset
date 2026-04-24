# AD Password Reset Application

[English](README.md) | 中文

一个基于 Web 的 Active Directory 用户密码重置应用，支持邮箱验证码验证、审计日志，以及加固后的密码重置流程。

## 功能特性

- 🔐 Active Directory 密码重置流程
- 📧 邮箱验证码发送与校验
- 🛡️ 密码重置成功 / 失败审计日志
- 🚀 React + TypeScript 前端界面
- 🔒 请求日志敏感字段脱敏
- ⏱️ 验证码发送冷却与错误次数限制

## 技术栈

- **后端**：Python + Flask
- **前端**：React + TypeScript + Vite
- **目录服务**：LDAP / Active Directory
- **邮件服务**：SMTP
- **测试**：pytest
- **日志**：Python logging + 滚动日志文件

## 环境要求

- Python 3.8+
- 推荐 Node.js 22 LTS
- Active Directory 环境
- SMTP 邮件服务

## 快速开始

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd AD_PassWord_Reset
   ```

2. **安装后端依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   在项目根目录创建 `.env`，至少包含：
   ```env
   LDAP_SERVER=...
   LDAP_PORT=636
   LDAP_BASE_DN=...
   LDAP_DOMAIN=...
   LDAP_USER=...
   LDAP_PASSWORD=...
   SMTP_SERVER=...
   SMTP_PORT=465
   SMTP_USERNAME=...
   SMTP_PASSWORD=...
   SERVER_IP=127.0.0.1
   SECRET_KEY=请替换为强随机值
   FLASK_ENV=production
   FLASK_DEBUG=False
   RATELIMIT_STORAGE_URI=memory://
   ```

4. **安装前端依赖**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

5. **运行应用**
   ```bash
   python run.py
   ```

   应用默认启动在 [http://localhost:5001](http://localhost:5001)。

## 推荐 Node 配置

本项目已使用 **Node.js 22 LTS** 验证通过。

如果你把 Node 安装在 `~/.local/node`，建议优先加入 PATH：

```bash
export PATH="$HOME/.local/node/node-v22.22.2-darwin-arm64/bin:$PATH"
```

## 前端命令

```bash
cd frontend
npm install
npm run dev
npm run build
```

## 后端测试

当前已补充与密码重置加固相关的最小回归测试：

```bash
$HOME/Library/Python/3.9/bin/pytest -q tests/test_auth_security.py
```

覆盖场景包括：

- `/api/verify-user` 返回掩码邮箱
- `/api/send-code` 仅依赖 `username`
- 验证码发送冷却限制
- 验证码连续输错后失效
- 缺失必填环境变量时配置校验失败

## 日志说明

应用日志输出到：

- `logs/app.log`
- `logs/audit.log`

当前日志行为：

- 请求 / 响应日志会脱敏密码、token、验证码、邮箱、Cookie 等敏感字段
- SMTP 发送日志会脱敏目标邮箱
- 审计日志会保留成功 / 失败事件，同时对 DN 做脱敏

如需在新一轮验证前清空日志：

```bash
: > logs/app.log
: > logs/audit.log
```

## 安全说明

- 不要提交 `.env` 文件或真实凭据。
- 生产环境请使用 LDAPS / 安全 SMTP。
- 建议定期检查审计日志。
- 当前验证码存储为进程内内存，服务重启后未完成的验证码会丢失。
- 历史旧日志不会因为新的脱敏规则而自动回写。

## 项目结构

```text
AD_PassWord_Reset/
├── backend/                # Flask 后端
│   ├── app.py
│   ├── config.py
│   ├── routes/
│   ├── services/
│   └── utils/
├── frontend/               # React + TypeScript 前端
├── logs/                   # 运行日志
├── tests/                  # pytest 回归测试
├── requirements.txt
└── run.py
```
