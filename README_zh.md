# AD Password Reset Application

[English](README.md) | 中文

一个基于Web的Active Directory用户密码重置应用程序，支持邮箱验证和安全的密码重置流程。

## 功能特性

- 🔐 安全的AD密码重置
- 📧 邮箱验证码验证
- 🛡️ 完整的审计日志
- 🚀 现代化的Web界面
- 📱 响应式设计
- 🔒 多层安全防护

## 技术栈

- **后端**: Python Flask
- **前端**: HTML5, CSS3, JavaScript
- **目录服务**: LDAP/Active Directory
- **邮件服务**: SMTP
- **日志**: Python logging

## 快速开始

### 环境要求

- Python 3.8+
- Active Directory环境
- SMTP邮件服务

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd AD_Reset
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   ```bash
   # 复制环境变量模板
   cp .env.example .env
   # 编辑 .env 文件，填写实际配置
   ```

5. **运行应用**
   ```bash
   python run.py
   ```

## 环境配置

### 必需的环境变量

复制 `.env.example` 为 `.env` 并配置以下变量：

#### LDAP配置
- `LDAP_SERVER`: AD服务器地址
- `LDAP_PORT`: LDAP端口 (通常为636或389)
- `LDAP_BASE_DN`: AD基础DN
- `LDAP_DOMAIN`: AD域名
- `LDAP_USER`: 管理员账号
- `LDAP_PASSWORD`: 管理员密码

#### SMTP配置
- `SMTP_SERVER`: 邮件服务器地址
- `SMTP_PORT`: SMTP端口
- `SMTP_USERNAME`: 发件人邮箱
- `SMTP_PASSWORD`: 邮箱密码

#### 应用配置
- `SERVER_IP`: 服务器IP地址
- `SECRET_KEY`: Flask密钥 (请使用强随机值)
- `FLASK_ENV`: 运行环境 (development/production)

## 安全注意事项

⚠️ **重要**: 
- 请确保 `.env` 文件不会被提交到版本控制系统
- 在生产环境中使用强密码和安全的密钥
- 定期检查审计日志
- 确保LDAP连接使用SSL加密

## 项目结构

```
AD_Reset/
├── backend/                # 后端代码
│   ├── app.py             # Flask应用主文件
│   ├── config.py          # 配置管理
│   ├── routes/            # 路由处理
│   ├── services/          # 业务逻辑服务
│   └── utils/             # 工具函数
├── frontend/              # 前端代码
├── logs/                  # 日志文件
├── .env.example          # 环境变量模板
├── requirements.txt      # Python依赖
└── run.py               # 应用启动文件
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 支持

如果您遇到问题或有建议，请创建 [Issue](../../issues)。
