# FutureData CTP 研究平台

## 项目状态

这是一个用于期货行情处理、K 线浏览和策略回测的单机研究平台。开发和发布均直接运行在 Windows 主机上；发布包自带 PostgreSQL、Python 运行时和已构建的 Web UI。

实盘 CTP 执行尚未达到生产可用状态。不要使用本项目连接真实经纪商账户，直到完成 CTP 原生依赖、SimNow 连通性、凭据管理、进程监管、回调处理与对账恢复的独立验收。

| 服务 | 用途 | 入口 |
| --- | --- | --- |
| PostgreSQL | 认证、控制与交易基础记录 | `127.0.0.1:5432` |
| API 与 UI | FastAPI 接口和已构建的 React UI | `127.0.0.1:8000` |
| 数据管道 | 按需执行 CSV 到 Parquet 的批处理 | 无监听端口 |

所有服务只绑定回环地址。如需远程使用，请通过受控的 Tailscale 或 SSH 隧道访问；不要改为公开监听。

## 本地开发

前置条件：Python 3.10+、Node.js 20.19+ 和 pnpm 10.33+。

首次准备环境：

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r appapi\requirements.txt
Set-Location appui
pnpm install
Set-Location ..
```

启动 API 与前端：

```powershell
python scripts\dev.py
```

浏览器访问 [http://127.0.0.1:5173](http://127.0.0.1:5173)。开发前端会把 `/api` 请求转发到 `http://127.0.0.1:8000`。

也可以单独启动一个部分：

```powershell
python scripts\dev.py api
python scripts\dev.py ui
python scripts\dev.py pipeline
```

数据管道直接读取 `data/input`，并写入 `data/output` 与 `data/market`。

## Windows 生产发布

发布工程师在构建机准备 Python for Windows 和 PostgreSQL for Windows 的完整发行目录；两者不会提交到 Git。构建发布包：

```powershell
python scripts\build_release.py --python-root C:\runtime-inputs\python --postgres-root C:\runtime-inputs\postgresql --output-root .\release\futuredata
```

将 `release\futuredata` 复制到目标主机后，一键启动：

```powershell
.\python\python.exe scripts\production.py start
```

首次启动自动创建发布目录外的 `runtime` 持久化目录、生成数据库密码与令牌密钥、初始化 PostgreSQL、创建数据库并应用初始架构。发布目录可以替换升级，不会覆盖 `runtime` 中的数据库、日志、备份或配置。

常用运维命令：

```powershell
.\python\python.exe scripts\production.py status
.\python\python.exe scripts\production.py logs
.\python\python.exe scripts\production.py backup
.\python\python.exe scripts\production.py restart
.\python\python.exe scripts\production.py stop
```

生产 UI 由 API 直接提供，入口为 [http://127.0.0.1:8000](http://127.0.0.1:8000)。不需要安装 Node、pnpm、独立 PostgreSQL 或其他运行服务。

## 验证

```powershell
# Python 行为验证（tests 目录按仓库规则不提交）
.\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider

# 前端检查与生产构建（appui 目录）
pnpm lint
pnpm build
```

## 目录说明

| 路径 | 说明 |
| --- | --- |
| `appapi` | FastAPI 路由、认证、行情查询与回测编排，以及生产 UI 托管 |
| `appui` | React/Vite UI、状态管理、图表与 API 客户端 |
| `data_pipeline` | CSV 清洗、聚合、质量报告与 Parquet 输出 |
| `market_data` | 兼容的行情读取与数据访问组件 |
| `quant_runtime` | 策略、指标、vn.py 导入和回测执行 |
| `deploy/native` | 发布运行时配置模板 |
| `deploy/postgres` | PostgreSQL 初始架构 |
| `scripts` | 开发、发布、运维与生成工具 |

## 架构文档

- [架构总览](docs/architecture/README.md)
- [组件边界](docs/architecture/components.md)
- [数据流](docs/architecture/data-flows.md)
- [开发与维护](docs/architecture/development.md)
- [技术栈](docs/architecture/tech-stack.md)
