# 原生 Windows 运行时重构设计

## 目标

将项目重构为不依赖 Docker 的 Windows 应用：本地开发直接使用宿主机工具链，生产发布包内置并管理 PostgreSQL。生产操作者通过一个 PowerShell 命令完成初始化与启动。

本设计覆盖平台 API、Web UI、行情数据管道和平台数据库；不改变实盘交易运行时的安全状态或宣称其实盘可用。

## 非目标

- 不保留 Docker、Docker Compose、Nginx 容器或其兼容启动入口。
- 不将真实凭据、数据库数据、日志或行情数据提交到版本库。
- 不把 PostgreSQL、Python 或 Node 的二进制文件提交到 Git。它们属于构建出的 Windows 发布包。
- 不把服务注册为 Windows Service。本次采用由启动脚本管理的后台进程。

## 运行模型

### 本地开发

`scripts/dev.ps1` 是开发入口，不调用 Docker。

1. 检查本机 Python 虚拟环境与前端依赖；缺失时给出可操作的安装提示。
2. 以当前工作区的 Python 直接启动 FastAPI/Uvicorn。
3. 在独立进程中启动 Vite，继续使用开发代理将 `/api` 转发给 API。
4. 可选子命令分别启动 API、UI 或数据管道，默认启动 API 与 UI。

开发数据库由操作者配置为已运行的本机 PostgreSQL。脚本不会下载、容器化或隐式创建数据库服务。

### 生产发布包

发布构建产生一个 Windows 发布目录，包含：

- 已构建的 Web 静态文件；
- 应用所需的 Python 运行环境与依赖；
- PostgreSQL for Windows 的二进制分发；
- 默认配置模板和 `scripts/production.ps1`。

API 在生产模式下直接托管 Web 静态文件和 SPA 回退路由，因此生产环境没有 Node、pnpm、Vite 或 Nginx 进程。服务仅绑定 `127.0.0.1`，远程访问仍须经受控的 SSH 或 Tailscale 隧道。

持久化运行目录由 `FUTUREDATA_RUNTIME_DIR` 配置，默认为发布目录外的 `runtime` 目录；其中保存 PostgreSQL 数据、运行时环境文件、日志、PID 和备份。升级时替换发布目录但不覆盖该目录。

## 生产命令

`scripts/production.ps1` 接受以下子命令：

| 命令 | 行为 |
| --- | --- |
| `start` | 校验配置、首次初始化数据库集群、启动 PostgreSQL 与 API，等待健康检查通过。 |
| `stop` | 先停止 API，再以正常方式停止 PostgreSQL。 |
| `restart` | 执行受控的 stop 后 start。 |
| `status` | 显示 PID、端口监听与健康端点结果。 |
| `logs` | 输出或跟随 API 与 PostgreSQL 日志。 |
| `backup` | 使用内置 `pg_dump` 将数据库备份到持久化目录。 |

`start` 是一键启动命令。首次运行时，它创建由访问控制保护的本地配置，要求操作者显式填入或生成数据库密码与 `AUTH_TOKEN_SECRET`，再继续启动；脚本不在终端、日志或仓库中回显秘密。

## 配置与数据流

生产脚本从持久化目录加载未跟踪的环境文件，并向 API 传入 PostgreSQL DSN、令牌密钥、行情根目录和日志目录。PostgreSQL 仅监听环回地址，API 使用同样的私有绑定。应用初始化 SQL 保持幂等，首次数据库初始化后自动执行。

行情数据仍由宿主机目录提供。生产 API 对数据目录只读；数据管道通过开发脚本或单独的生产维护命令直接运行，沿用原有原子写入行为。

## Docker 清理范围

删除以下 Docker 专用内容并替换引用：

- `deploy/compose.platform.yml` 与 `deploy/compose.live-trading.yml`；
- `deploy/**/Dockerfile`、Nginx 配置、Compose 环境模板和 Docker 忽略文件；
- README、架构文档、测试和脚本中的 Docker/Compose 命令或“容器化”表述。

保留 `deploy` 目录仅存放原生 Windows 发布构建与 PostgreSQL 初始化资产；若重构后没有合理的部署资产，则移除该目录。

## 错误处理与恢复

- 配置缺失、端口占用、运行目录不可写、数据库启动失败或健康检查超时必须返回非零退出码，并给出下一步修复提示。
- PID 文件只能在确认进程不再存活时清除，避免误杀其他进程。
- 启动失败后脚本停止本次已启动的子进程，保留日志和数据目录供诊断。
- `backup` 先验证数据库可连接，再写入带时间戳的备份文件；不覆盖已有备份。

## 验收与测试

1. 在未安装 Docker 的 Windows 开发机上，开发脚本能启动 API 与 Vite，前端可调用 API。
2. 发布包在未安装 Docker、Node、pnpm 或独立 PostgreSQL 的 Windows 主机上，通过 `production.ps1 start` 完成首次初始化并提供健康端点与 UI。
3. `stop`、`restart`、`status`、`logs` 与 `backup` 的成功和常见失败路径均有自动化测试或脚本级验证。
4. 数据库和配置在替换发布目录后仍保持可用；发布包不会包含本地数据、日志或秘密。
5. 仓库不再包含 Dockerfile、Compose 文件、Docker 专用配置或对 Docker/Compose 的运行时引用。

## 实施边界

实现将分为部署脚本与运行时配置、API 静态文件托管、发布构建、Docker 资产清理、文档迁移和测试六个相互可验证的部分。发布包的实际二进制下载或发布渠道不在本次代码库内决定；构建流程只定义其输入目录与可复现的组装步骤。
