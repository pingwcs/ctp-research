# 简化启动器环境配置设计

## 目标

消除 Python 启动器中的 DSN、端口、路径和运行时默认值硬编码。开发和生产各使用一个完整 `.env` 文件，格式一致，启动器仅加载、校验和使用配置。

## 配置文件

| 环境 | 文件 | 版本控制 |
| --- | --- | --- |
| 开发 | `deploy/native/dev.env` | 跟踪；仅含本机安全默认值。 |
| 生产 | `deploy/native/prod.env` | 跟踪；秘密使用 `CHANGE_ME` 占位符。 |

两个文件都定义：`APPAPI_HOST`、`APPAPI_PORT`、`MARKET_DATA_DIR`、`MARKET_LOG_DIR`、`APPUI_DIST_DIR`、`POSTGRES_USER`、`POSTGRES_DB`、`POSTGRES_PASSWORD`、`PLATFORM_POSTGRES_DSN` 与 `AUTH_TOKEN_SECRET`。

发布构建把 `prod.env` 复制到发布包。部署操作者在目标主机编辑该文件填入真实秘密；`production.py` 在检测到任一秘密仍为 `CHANGE_ME` 时退出并给出错误。该文件位于发布包，而不是部署机上的 Git 工作副本。

## 实现

新增一个小型 `scripts/runtime_config.py` module，公开 `load_env(path)`：读取 `KEY=VALUE` 行，忽略空行和注释，拒绝重复或缺失的必填键，拒绝生产配置中的占位符秘密，并将相对路径相对于配置文件解析。`dev.py` 只加载 `dev.env`，`production.py` 只加载 `prod.env`，`build_release.py` 只复制配置文件。

## 验收

- 三个 Python 启动器不含 DSN、端口、路径或秘密值字面量。
- 开发和生产配置文件都被 Git 追踪且格式一致。
- 生产启动在未替换秘密占位符时以退出码 2 拒绝运行。
- 未跟踪行为测试覆盖配置加载、缺少键和占位符拒绝。
