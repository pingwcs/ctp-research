#!/usr/bin/env python3
import os
import sys

# 配置项
MAX_LINE_LENGTH = 79
EXCLUDE_DIRS = {".git", "venv", "__pycache__", "build", "dist", ".pytest_cache"}
PY_SUFFIX = ".py"


def find_py_files(root_path: str) -> list[str]:
    """遍历项目获取所有py文件，跳过排除目录"""
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # 移除需要跳过的目录，避免递归进入
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            if fname.endswith(PY_SUFFIX):
                full_path = os.path.abspath(os.path.join(dirpath, fname))
                py_files.append(full_path)
    return py_files


def check_file(file_path: str) -> int:
    """检查单个文件，返回错误数量"""
    err_count = 0
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"\033[31m[ERROR] 无法读取文件 {file_path}: {e}\033[0m")
        return 1

    for line_no, raw_line in enumerate(lines, start=1):
        line_stripped = raw_line.rstrip("\n")
        # 1. 行尾尾随空格
        if line_stripped.endswith(" "):
            print(f"\033[33m[WARN] {file_path}:{line_no} 存在行尾尾随空格\033[0m")
            err_count += 1
        # 2. Tab缩进禁止
        if "\t" in raw_line:
            print(
                f"\033[31m[ERROR] {file_path}:{line_no} 使用Tab缩进，请改用4空格\033[0m"
            )
            err_count += 1
        # 3. 单行超过79字符
        line_len = len(line_stripped)
        if line_len > MAX_LINE_LENGTH:
            print(
                f"\033[31m[ERROR] {file_path}:{line_no} 行长度{line_len} > {MAX_LINE_LENGTH}\033[0m"
            )
            err_count += 1
    return err_count


def main():
    project_root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    py_files = find_py_files(project_root)
    total_err = 0

    print(
        f"开始检查Python文件，共{len(py_files)}个文件，单行限制{MAX_LINE_LENGTH}字符\n"
    )
    for f in py_files:
        total_err += check_file(f)

    if total_err > 0:
        print(
            f"\n\033[31m检查失败，共 {total_err} 处格式问题，请修复后再提交推送\033[0m"
        )
        sys.exit(1)
    else:
        print("\n\033[32m所有Python代码格式检查通过\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
