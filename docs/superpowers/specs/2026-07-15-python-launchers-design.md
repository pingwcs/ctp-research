# Python 启动器迁移设计

## 目标

将 Windows 开发、发布组装和生产运维入口统一为 Python 脚本，并删除对应的 PowerShell 脚本。操作者通过 Python 解释器运行脚本，不再依赖 PowerShell 作为项目启动器。

## 入口

| 现有入口 | 新入口 | 用途 |
| --- | --- | --- |
| `scripts/dev.ps1` | `scripts/dev.py` | 本地启动 API、Vite 或数据管道。 |
| `scripts/build-release.ps1` | `scripts/build_release.py` | 构建 UI 并组装 Windows 发布目录。 |
| `scripts/production.ps1` | `scripts/production.py` | 管理发布包内 PostgreSQL、API、日志与备份。 |

开发者运行 `python scripts/dev.py`。发布构建仍由构建机的 Python 运行 `python scripts/build_release.py`；生产目标机使用发布包中的 `python\\python.exe scripts\\production.py start`。

## 实现边界

Python 脚本使用标准库 `argparse`、`pathlib`、`subprocess`、`secrets`、`urllib` 和 `shutil`。它们保留现有命令、路径、环境文件格式、端口、PID 文件、日志文件、健康检查、初始化 SQL 和备份行为。

`production.py` 以 `subprocess.Popen` 启动 PostgreSQL 和 API，并把各自的 PID 写入持久化运行目录。停止操作只处理脚本记录的 PID，并通过 `pg_ctl` 正常关闭数据库。首次启动仍在发布目录外生成秘密配置，绝不输出秘密。

## 错误处理与验证

三个脚本都返回明确的退出码：参数或运行时输入错误为 2，启动或构建失败为 1，成功为 0。Windows 路径与命令调用通过 `pathlib.Path` 和参数列表处理，不拼接 shell 命令。

未跟踪的 pytest 行为测试验证无效参数、缺失发布运行时、静态 UI 托管和无旧脚本残留。验证还包括前端 lint/build、OpenAPI 生成路径、以及 API 托管 SPA 的回环冒烟测试。

## 文档与清理

README、架构文档、发布模板和发布构建复制规则全部更新为 `.py` 命令。删除三份 `.ps1` 源脚本及其 PowerShell 测试；仓库不再引用 `.ps1` 启动器。
