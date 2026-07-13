# FutureData CTP 研究平台

## 项目状态

这是一个用于期货行情处理、K 线浏览和策略回测的单机研究平台。前端与 API 已容器化，可通过 **Docker 私有平台** 在本机回环地址访问；行情文件由操作者配置的持久目录提供。

实盘 CTP 执行尚未达到生产可用状态。不要使用本项目连接真实经纪商账户，直到完成 CTP 原生依赖、SimNow 连通性、凭据管理、进程监管、回调处理与对账恢复的独立验收。

| 服务 | 用途 | 宿主机入口 |
| --- | --- | --- |
| `postgres` | 认证、控制与交易基础记录 | `127.0.0.1:5432` |
| `appapi` | FastAPI 行情查询与回测编排 | `127.0.0.1:8000` |
| `appui` | React 静态站点与同源 API 代理 | `127.0.0.1:5173` |
| `pipeline` | 按需执行 CSV 到 Parquet 的批处理 | 不发布端口 |

所有发布端口均只绑定回环地址，不能直接从局域网或公网访问。如需远程使用，请通过受控的 Tailscale 或 SSH 隧道访问本机端口；不要把 Compose 端口改为 `0.0.0.0`。

## Docker 私有平台

### 前置条件

- Docker Desktop 或 Docker Engine，且已启用 Docker Compose v2。
- 用于保存行情数据的本地持久目录；它不能提交到 Git。
- 可选：PowerShell（以下命令以 Windows PowerShell 为例）。

### 创建运行时环境文件

从模板创建未跟踪的运行时文件，并编辑其中的占位符：

```powershell
Copy-Item deploy\env\platform.env.example deploy\env\platform.env
```

在 `deploy/env/platform.env` 中：

1. 将 `PLATFORM_ENV_FILE` 改为 `./env/platform.env`。
2. 为 `POSTGRES_PASSWORD` 填入本机专用密码，并在 `PLATFORM_POSTGRES_DSN` 中填入相同的已编码密码。
3. 设置 `AUTH_TOKEN_SECRET`。可用下列命令生成随机值：

   ```powershell
   [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
   ```

4. 设置 `PLATFORM_DATA_DIR` 为数据根目录。模板的 `../data` 对应仓库外的 `data` 目录；也可以改为绝对路径。

不要在仓库、模板、日志或 issue 中写入数据库密码、令牌或 CTP 凭据。

### 验证、构建和启动

先验证 Compose 插值与服务定义：

```powershell
docker compose -f deploy/compose.platform.yml --env-file deploy/env/platform.env config
```

构建并在后台启动 PostgreSQL、API 和 UI：

```powershell
docker compose -f deploy/compose.platform.yml --env-file deploy/env/platform.env up --build -d
```

确认健康状态：

```powershell
Invoke-WebRequest http://127.0.0.1:5173/health
Invoke-WebRequest http://127.0.0.1:8000/health
```

浏览器访问 [http://127.0.0.1:5173](http://127.0.0.1:5173)。UI 通过同源的 `/api/` 请求反向代理到 API，浏览器无需知道容器服务名或 API 地址。API 尚未就绪时，Nginx 会返回普通网关错误；API 恢复后不需要重建 UI。

查看日志和停止平台：

```powershell
docker compose -f deploy/compose.platform.yml --env-file deploy/env/platform.env logs -f
docker compose -f deploy/compose.platform.yml --env-file deploy/env/platform.env down
```

`down` 不会删除 PostgreSQL 命名卷；如需清除本机数据库，请在确认数据可丢弃后自行删除对应卷。

### 按需运行数据管道

数据管道使用 Compose profile，平台启动时不会自动执行。需要转换数据时运行：

```powershell
docker compose -f deploy/compose.platform.yml --env-file deploy/env/platform.env --profile pipeline run --rm pipeline
```

数据根目录的约定如下：

```text
data/
├── input/       # 原始 CSV，pipeline 读取
├── output/      # 兼容的 1min、5min Parquet，API 只读使用
└── market/      # pipeline 写出的规范分区 Parquet
```

`pipeline` 对整个数据根目录具有读写权限，并沿用既有的原子写入逻辑，因此失败不会替换已成功发布的 Parquet。`appapi` 仅以只读方式挂载 `output` 到 `/workspace/data/output`；UI、API 和 PostgreSQL 均没有行情文件写入权限。当前 API 仍从兼容布局的 `output/5min` 读取 K 线、从 `output/1min` 读取回测数据；`market` 暂不作为 API 的读取入口。

## 本地开发

Docker 是私有部署主路径；本地 Python/Vite 方式适用于开发和调试。

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r appapi\requirements.txt
python -m appapi.main
```

未设置 `APPAPI_HOST` 时，API 默认监听 `127.0.0.1:8000`。另开一个终端运行 UI：

```powershell
cd appui
pnpm install
pnpm dev
```

本地 Vite 默认提供 `http://127.0.0.1:5173`。若直接执行数据管道，可使用：

```powershell
python data_pipeline\run.py --input-dir data/input --output-dir data/output --market-root data/market --no-influx
```

## 验证与测试

```powershell
# Python 测试（仓库根目录）
.\venv\Scripts\python.exe -m pytest -q

# 前端静态检查与生产构建（appui 目录）
pnpm lint
pnpm build

# Compose 配置解析
docker compose -f deploy/compose.platform.yml --env-file deploy/env/platform.env config
```

## 目录说明

| 路径 | 说明 |
| --- | --- |
| `appapi` | FastAPI 路由、认证、行情查询与回测编排 |
| `appui` | React/Vite UI、状态管理、图表与 API 客户端 |
| `data_pipeline` | CSV 清洗、聚合、质量报告与 Parquet 输出 |
| `market_data` | 兼容的行情读取与数据访问组件 |
| `quant_runtime` | 策略、指标、vn.py 导入和回测执行 |
| `deploy` | 私有平台 Compose、容器镜像与环境模板 |
| `tests` | 跨子系统行为与部署契约测试 |

## 架构文档

- [架构总览](docs/architecture/README.md)
- [组件边界](docs/architecture/components.md)
- [数据流](docs/architecture/data-flows.md)
- [开发与维护](docs/architecture/development.md)
- [技术栈](docs/architecture/tech-stack.md)
