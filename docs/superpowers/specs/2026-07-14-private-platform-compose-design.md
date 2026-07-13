# 私有部署平台 Compose 设计

## 目标

将当前项目部署为单机、私有网络可访问的平台。Docker Compose 提供 PostgreSQL、FastAPI API、React UI 和按需运行的数据处理服务；保留本机 Python/Vite 开发方式作为补充。所有数据、密码、令牌和 CTP 凭据均留在 Git 之外。

## 范围与非目标

本次交付修复 API 容器监听地址、容器化 UI、以可选服务运行数据管道，并重写中文 README。它不实现实盘 CTP 执行、不将 Tick/K 线写入 PostgreSQL，也不迁移 API 到新的分区行情读取格式。

当前 API 仍从兼容布局 `data/output/5min` 读取 K 线、从 `data/output/1min` 读取回测数据。数据管道同时可以写出规范分区 `data/market`，但该目录暂不作为 API 的读取入口。

## 服务与网络

`deploy/compose.platform.yml` 定义以下服务：

| 服务 | 职责 | 容器内端口 | 宿主机端口 |
| --- | --- | --- | --- |
| `postgres` | 认证、控制与交易基础记录 | 5432 | `127.0.0.1:5432` |
| `appapi` | FastAPI HTTP API、行情查询与回测编排 | 8000 | `127.0.0.1:8000` |
| `appui` | 静态 React UI 与同源 API 反向代理 | 8080 | `127.0.0.1:5173` |
| `pipeline` | 按需 CSV 到 Parquet 批处理 | 无 | 无 |

API 继续以 `python -m appapi.main` 启动。应用入口读取 `APPAPI_HOST`：本机未设置时绑定 `127.0.0.1`；API Docker 镜像设为 `0.0.0.0`，以接收 Compose 网络转发。Compose 的端口发布仍只使用回环地址，不能改为公网绑定。远程访问只能通过受控的 Tailscale 或 SSH 隧道。

## UI 容器

UI 采用多阶段镜像：Node 构建阶段以锁文件安装 `pnpm` 依赖并运行 `pnpm build`；运行阶段使用非 root Nginx 提供 `dist` 文件。Nginx 处理 SPA 回退到 `index.html`，将 `/api/` 代理至 `http://appapi:8000`，并将 `/health` 代理至 API 的健康检查。浏览器只访问同源相对路径，不需要知道容器服务名或 API 地址。

`appui` 在 `appapi` 已启动后运行。API 尚未就绪时，Nginx 应返回正常的网关错误而不是缓存失败响应；API 恢复后无需重建 UI 即可继续服务。

## 行情数据与处理管道

环境文件提供 `PLATFORM_DATA_DIR`，默认指向项目数据根目录。该目录不提交到 Git：

```text
data/
├── input/       # 原始 CSV
├── output/      # 兼容的 1min、5min Parquet，API 只读使用
└── market/      # 数据管道写出的规范分区 Parquet
```

`pipeline` 通过 Compose profile 声明，默认不随平台启动。它以读写方式挂载整个数据根目录到 `/data`，从 `/data/input` 读取，向 `/data/output` 和 `/data/market` 写入。`appapi` 仅以只读方式挂载宿主机的 `output` 目录至 `/workspace/data/output`，并通过 `MARKET_DATA_DIR=/workspace/data/output` 保持既有 K 线读取器兼容。

管道执行失败不能替换已有成功发布的 Parquet；已有的原子写入逻辑继续承担此保证。API 容器、UI 容器和 PostgreSQL 都不得拥有行情文件写权限。

## 配置与机密

操作者从 `deploy/env/platform.env.example` 复制出未跟踪的 `deploy/env/platform.env`。该文件包含数据库名称、用户、密码、容器内 PostgreSQL DSN、`AUTH_TOKEN_SECRET`、`PLATFORM_DATA_DIR` 和 `PLATFORM_ENV_FILE`。模板只能保留明显的占位符，README 说明如何生成随机令牌；不得写入任何可用密码、令牌或 CTP 凭据。

## README

README 使用中文，以 Docker 私有平台为主路径：前置条件、环境文件创建、配置验证、构建与启动、UI/API 健康检查、按需运行数据管道、日志和停止命令。它会明确说明：实盘 CTP 尚未达到生产可用状态；所有发布端口仅限本机；前端与 API 已容器化；行情数据来自用户配置的持久目录。本机 Python/Vite 开发、测试和架构文档作为补充章节。

## 验证策略

1. 为 `APPAPI_HOST` 增加单元测试，验证默认回环绑定和环境覆盖。
2. 扩展部署合约测试，验证四个服务、三个回环端口、非 root UI 镜像、Nginx 代理、`pipeline` profile、数据挂载的读写权限、无机密模板和 API Docker 环境。
3. 执行 Python 测试、`pnpm lint` 与 `pnpm build`。
4. 执行 `docker compose -f deploy/compose.platform.yml --env-file deploy/env/platform.env.example config`。
5. 在具备 Docker 镜像拉取条件的主机上，执行 `up --build -d`，确认 `http://127.0.0.1:5173/health` 与 `http://127.0.0.1:8000/health` 返回成功；完成后停止服务。

## 验收标准

- API 在容器内可通过服务网络访问，宿主机仍只从回环地址访问。
- UI 可由 `http://127.0.0.1:5173` 提供，并能同源代理 API。
- 数据管道不会常驻运行，且 API 对兼容 Parquet 目录没有写权限。
- README 的每条主路径命令与 Compose 文件、环境模板及实际端口一致。
- 全部可用自动化验证通过，且不新增真实机密。
