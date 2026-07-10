"""Runtime settings for the standalone quant runtime package.

业务功能: 汇总 quant_runtime 的数据目录、运行时目录和 vn.py 数据库配置。
算法要点: VNPY 依赖当前工作目录和用户目录样式的 .vntrader 状态，本模块把
这些状态固定到 quant_runtime/runtime 下，避免污染开发者真实环境。
"""

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from global_config import load_environment_config


@dataclass(frozen=True)
class QuantRuntimeSettings:
    """业务功能: quant_runtime 运行所需的不可变配置快照。"""

    repo_root: Path
    minute_data_dir: Path
    runtime_dir: Path
    database_name: str

    @property
    def vntrader_dir(self) -> Path:
        """业务功能: 返回 vn.py 使用的 .vntrader 状态目录。"""
        return self.runtime_dir / ".vntrader"


def load_settings(environ=None) -> QuantRuntimeSettings:
    """业务功能: 从统一环境配置装配 quant_runtime 设置。"""
    env_config = load_environment_config(environ)
    return QuantRuntimeSettings(
        repo_root=env_config.project_root,
        minute_data_dir=env_config.quant_runtime_minute_data_dir,
        runtime_dir=env_config.quant_runtime_dir,
        database_name=env_config.quant_runtime_database,
    )


settings = load_settings()


def ensure_runtime_dirs() -> None:
    """业务功能: 确保 quant_runtime 和 .vntrader 状态目录存在。"""
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    settings.vntrader_dir.mkdir(parents=True, exist_ok=True)


def prepare_vnpy_runtime() -> None:
    """业务功能: 准备 vn.py 策略和数据库模块的运行环境。

    算法要点: 将 repo 根目录加入 sys.path 以支持 class_path 动态导入，并把
    cwd 切到 runtime_dir，让 vn.py 的相对状态文件落在受控目录。
    """
    ensure_runtime_dirs()
    repo_root = str(settings.repo_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    os.chdir(settings.runtime_dir)
