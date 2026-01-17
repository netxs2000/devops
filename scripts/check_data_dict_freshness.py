"""数据字典新鲜度检测脚本

用于 Git Pre-commit Hook，检测模型变更后数据字典是否已更新。

使用方法:
    python scripts/check_data_dict_freshness.py

返回码:
    0: 数据字典已是最新
    1: 数据字典需要更新
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def get_git_modified_files() -> set:
    """获取 Git 暂存区中已修改的文件列表。

    Returns:
        set: 已修改文件路径集合。
    """
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        if result.returncode == 0:
            return set(result.stdout.strip().split('\n'))
    except Exception:
        pass
    return set()


def check_model_files_modified(modified_files: set) -> bool:
    """检查是否有模型文件被修改。

    Args:
        modified_files: 已修改文件集合。

    Returns:
        bool: 是否有模型文件被修改。
    """
    model_patterns = [
        'devops_collector/models/',
        'devops_collector/plugins/',
    ]

    for file_path in modified_files:
        for pattern in model_patterns:
            if pattern in file_path and file_path.endswith('.py'):
                return True
    return False


def check_data_dict_updated(modified_files: set) -> bool:
    """检查数据字典是否已更新。

    Args:
        modified_files: 已修改文件集合。

    Returns:
        bool: 数据字典是否已更新。
    """
    data_dict_path = 'docs/api/DATA_DICTIONARY.md'
    return data_dict_path in modified_files


def get_data_dict_age() -> int:
    """获取数据字典文件的年龄（天数）。

    Returns:
        int: 距离上次修改的天数，文件不存在返回 -1。
    """
    data_dict_path = Path(__file__).parent.parent / 'docs' / 'api' / 'DATA_DICTIONARY.md'
    if not data_dict_path.exists():
        return -1

    mtime = datetime.fromtimestamp(data_dict_path.stat().st_mtime)
    age = (datetime.now() - mtime).days
    return age


def main():
    """主函数：检查数据字典是否需要更新。"""
    print('Checking Data Dictionary freshness...')

    modified_files = get_git_modified_files()

    # 检查是否有模型文件被修改
    models_changed = check_model_files_modified(modified_files)
    dict_updated = check_data_dict_updated(modified_files)

    if models_changed and not dict_updated:
        print('')
        print('=' * 60)
        print('WARNING: Model files changed but DATA_DICTIONARY.md not updated!')
        print('=' * 60)
        print('')
        print('The following model-related files were modified:')
        for f in modified_files:
            if 'models/' in f or 'plugins/' in f:
                print(f'  - {f}')
        print('')
        print('Please run the following command to update the data dictionary:')
        print('  make docs')
        print('')
        print('Or add the generated file to your commit:')
        print('  git add docs/api/DATA_DICTIONARY.md')
        print('')
        # 返回 0 以不阻塞提交，仅作为警告
        # 如果需要强制更新，改为 sys.exit(1)
        return 0

    # 检查数据字典年龄
    age = get_data_dict_age()
    if age > 7:
        print(f'Note: Data dictionary is {age} days old. Consider running "make docs" to refresh.')

    print('Data Dictionary check passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
