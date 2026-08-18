# AD Password Reset Application

[English](README.md) | 中文

一个基于 Flask、React 和 Active Directory 的自助密码重置应用。验证码与一次性重置事务保存在当前进程内，不依赖 Redis。

## 安全特性

- 仅允许验证服务器证书的 LDAPS，不会降级到明文 LDAP
- 每次 LDAP 操作使用独立连接，避免多线程共享连接状态
- 使用密码学安全随机数生成验证码和重置令牌
- 验证码、冷却、失败次数和令牌消费均受进程内锁保护
- 重置令牌有效期短且只能使用一次
- 用户存在与否返回相同的验证码请求响应
- 后端强制密码策略、CSRF 校验、请求体大小限制和安全响应头
- 应用日志不记录请求头、请求体、验证码、令牌或密码

## 运行要求

- Python 3.12
- Node.js 22 LTS
- 可通过 LDAPS 访问的 Active Directory
- 支持 TLS 且证书可信的 SMTP 服务

## 本地启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# 编辑 .env，填写真实配置并生成 SECRET_KEY

cd frontend
npm ci
npm run build
cd ..

python run.py
```

默认仅监听 [http://127.0.0.1:5002](http://127.0.0.1:5002)。

## 配置迁移说明

安全重构后，以下配置是强制要求：

- `SECRET_KEY` 必须至少 32 个字符，且不能使用示例值
- `LDAP_USE_SSL=true`
- `LDAP_VERIFY_CERT=true`
- `LDAP_DOMAIN` 和 `LDAP_AUTH_MODE` 必须明确配置
- 内部 CA 未安装到系统信任链时，需要设置 `LDAP_CA_CERT_PATH`
- SMTP 证书验证不能关闭

如果旧 `.env` 中包含 `LDAP_VERIFY_CERT=false`，应用会拒绝启动。请先部署可信 CA，不要通过关闭校验恢复运行。

如果短期内无法更换旧 SHA-1 证书，可以显式启用 `LDAP_COMPATIBILITY_MODE=true`，并通过 `LDAP_CERT_SHA256` 固定当前证书指纹。兼容模式会在发送绑定凭据前校验证书指纹，但它仍是临时方案：证书更新后必须同步更新指纹，长期仍应迁移到受信任的 SHA-256 证书。

## 单进程限制

按当前设计，验证码、一次性重置令牌和速率限制均使用进程内存储：

- 只能运行一个 Waitress 应用进程，但可以使用多个线程
- 不支持多实例或水平扩容
- 服务重启后，未完成的验证码与重置事务会失效
- 如果未来需要多实例部署，必须先替换为共享且支持原子操作的状态存储

## 验证命令

```bash
pytest -q

cd frontend
npm run lint
npm run build
npm audit --omit=dev
cd ..

pip-audit -r requirements.txt
```

## 生产部署

- 桌面/单机模式保持 `SERVER_HOST=127.0.0.1` 和 `COOKIE_SECURE=false`
- 对外服务必须部署在 HTTPS 反向代理后，设置 `SERVER_HOST=0.0.0.0` 与 `COOKIE_SECURE=true`
- 反向代理应限制来源网络、请求大小和连接速率
- LDAP 服务账号只授予目标 OU 的密码重置权限
- 定期轮换 LDAP、SMTP 凭据与 `SECRET_KEY`
- 监控并妥善保留 `logs/app.log` 和 `logs/audit.log`

## 打包发布

`.github/workflows/release.yml` 会在构建前运行后端测试、前端 lint/build 和依赖审计，然后生成 Windows 与 macOS 包。推送 `v*` 标签时会发布 GitHub Release。

macOS 包当前未签名或 notarize，正式分发前仍需补充签名流程。

打包运行时，Windows 将 `.env` 放在程序目录；macOS 将 `.env` 放在 `.app` 文件旁边。
