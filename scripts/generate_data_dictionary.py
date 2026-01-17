"""数据字典自动生成器 (Data Dictionary Generator) - 增强版 v2.2

基于 SQLAlchemy 模型反射，自动生成企业级数据字典文档。

功能特性:
    - 自动扫描所有 ORM 模型
    - 提取表结构、字段类型、约束、关系
    - 生成 Markdown 格式的标准化文档
    - 支持变更检测和 Diff 对比
    - 支持增量更新记录
"""
import sys
import inspect
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect as sa_inspect
from devops_collector.models.base_models import Base
from devops_collector import models


def get_column_type_description(column) -> str:
    """获取列类型的友好描述。

    Args:
        column: SQLAlchemy Column 对象。

    Returns:
        str: 类型描述字符串（如 "String(200)"）。
    """
    col_type = str(column.type)
    type_mapping = {
        'VARCHAR': 'String',
        'INTEGER': 'Integer',
        'BOOLEAN': 'Boolean',
        'DATETIME': 'DateTime',
        'UUID': 'UUID',
        'JSONB': 'JSONB',
        'JSON': 'JSON',
        'FLOAT': 'Numeric',
        'NUMERIC': 'Numeric',
        'TEXT': 'Text',
        'BIGINT': 'BigInteger',
        'DATE': 'Date',
    }
    for key, value in type_mapping.items():
        if key in col_type:
            if key == 'VARCHAR':
                return col_type.replace('VARCHAR', 'String')
            return value
    return col_type


def get_column_constraints(column) -> List[str]:
    """获取列的约束信息。

    Args:
        column: SQLAlchemy Column 对象。

    Returns:
        List[str]: 约束列表（如 ['PK', 'NOT NULL']）。
    """
    constraints = []
    if column.primary_key:
        constraints.append('PK')
    if column.foreign_keys:
        constraints.append('FK')
    if column.unique:
        constraints.append('UNIQUE')
    if column.index:
        constraints.append('INDEX')
    return constraints


def extract_docstring_description(model_class) -> str:
    """从模型类的 docstring 提取业务描述。

    Args:
        model_class: SQLAlchemy 模型类。

    Returns:
        str: 业务描述文本。
    """
    doc = inspect.getdoc(model_class)
    if not doc:
        return '无描述'
    lines = doc.split('\n')
    description = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('Attributes:') and not line.startswith('Args:'):
            description.append(line)
        elif line.startswith('Attributes:'):
            break
    return ' '.join(description) if description else '无描述'


def generate_table_documentation(model_class) -> Dict[str, Any]:
    """为单个模型生成表文档。

    Args:
        model_class: SQLAlchemy 模型类。

    Returns:
        Dict[str, Any]: 包含表信息的字典。
    """
    mapper = sa_inspect(model_class)
    table_name = model_class.__tablename__
    description = extract_docstring_description(model_class)

    columns_info = []
    for column in mapper.columns:
        # 获取 comment (字段注释)
        comment = getattr(column, 'comment', None) or '-'
        
        col_info = {
            'name': column.name,
            'type': get_column_type_description(column),
            'constraints': get_column_constraints(column),
            'nullable': column.nullable,
            'default': str(column.default.arg) if column.default and hasattr(column.default, 'arg') else '-',
            'comment': comment
        }
        columns_info.append(col_info)

    relationships_info = []
    for rel_name, rel in mapper.relationships.items():
        relationships_info.append({
            'name': rel_name,
            'target': rel.mapper.class_.__name__,
            'type': 'one-to-many' if rel.uselist else 'many-to-one'
        })

    return {
        'table_name': table_name,
        'model_class': model_class.__name__,
        'description': description,
        'columns': columns_info,
        'relationships': relationships_info
    }


def generate_markdown_table(columns_info: List[Dict]) -> str:
    """生成 Markdown 格式的表格。

    Args:
        columns_info: 列信息列表。

    Returns:
        str: Markdown 表格字符串。
    """
    md = '| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |\n'
    md += '|:-------|:---------|:-----|:-----|:-------|:-----|\n'
    for col in columns_info:
        constraints_str = ', '.join(col['constraints']) if col['constraints'] else '-'
        nullable_str = '是' if col['nullable'] else '否'
        # 清理默认值显示
        default_val = col['default']
        if 'function' in default_val or 'lambda' in default_val:
            default_val = '(auto)'
        md += f"| `{col['name']}` | {col['type']} | {constraints_str} | {nullable_str} | {default_val} | {col['comment']} |\n"
    return md


def extract_table_names_from_content(content: str) -> Set[str]:
    """从 Markdown 内容中提取表名列表。

    Args:
        content: Markdown 文档内容。

    Returns:
        Set[str]: 表名集合。
    """
    import re
    pattern = r'### \w+ \(`(\w+)`\)'
    return set(re.findall(pattern, content))


def generate_changelog(old_path: Path, new_tables: Set[str]) -> Tuple[str, List[str]]:
    """对比新旧数据字典，生成变更摘要。

    Args:
        old_path: 旧版数据字典路径。
        new_tables: 新版表名集合。

    Returns:
        Tuple[str, List[str]]: 变更摘要和详细变更列表。
    """
    if not old_path.exists():
        return "初始版本", [f"+ 新增 {len(new_tables)} 个数据表"]

    old_content = old_path.read_text(encoding='utf-8')
    old_tables = extract_table_names_from_content(old_content)

    added = new_tables - old_tables
    removed = old_tables - new_tables

    changes = []
    if added:
        for t in sorted(added):
            changes.append(f"+ 新增表: `{t}`")
    if removed:
        for t in sorted(removed):
            changes.append(f"- 移除表: `{t}`")

    if not changes:
        changes.append("无结构性变更")
        summary = "无结构性变更"
    else:
        summary = f"新增 {len(added)} 个表, 移除 {len(removed)} 个表"

    return summary, changes


def categorize_models(all_models: List) -> Dict[str, List]:
    """按业务域对模型进行分类。

    Args:
        all_models: 所有模型类列表。

    Returns:
        Dict[str, List]: 分类后的模型字典。
    """
    categories = {
        '核心主数据域': [],
        '测试管理域': [],
        'GitLab 集成域': [],
        '认证与授权域': [],
        '分析与洞察域': [],
        '其他辅助域': []
    }

    for model in all_models:
        table_name = model.__tablename__

        if 'mdm_' in table_name or table_name in ['organizations', 'products', 'services']:
            categories['核心主数据域'].append(model)
        elif 'gitlab_' in table_name or table_name in ['sync_logs']:
            categories['GitLab 集成域'].append(model)
        elif 'test_' in table_name or 'requirement' in table_name or 'gtm_' in table_name:
            categories['测试管理域'].append(model)
        elif 'auth_' in table_name or 'credential' in table_name or 'sys_user' in table_name:
            categories['认证与授权域'].append(model)
        elif 'view_' in table_name or 'okr_' in table_name or 'fct_' in table_name:
            categories['分析与洞察域'].append(model)
        else:
            categories['其他辅助域'].append(model)

    return categories


def generate_full_data_dictionary() -> Tuple[str, Set[str]]:
    """生成完整的数据字典文档。

    Returns:
        Tuple[str, Set[str]]: Markdown 格式数据字典和表名集合。
    """
    # 收集所有模型
    all_models = []
    for name, obj in inspect.getmembers(models):
        if inspect.isclass(obj) and hasattr(obj, '__tablename__') and obj != Base:
            all_models.append(obj)

    all_models.sort(key=lambda m: m.__tablename__)
    table_names = {m.__tablename__ for m in all_models}

    # 按业务域分类
    categories = categorize_models(all_models)

    # 开始生成文档
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    md = f"""# DevOps 效能平台 - 数据字典 (Data Dictionary)

> **生成时间**: {now}  
> **版本**: v2.2 (企业级标准版)  
> **状态**: 有效 (Active)

---

## 文档说明

本数据字典基于系统最新的 SQLAlchemy ORM 模型自动生成，确保与实际数据库结构的一致性。

### 文档结构
- **表名**: 数据库表的物理名称
- **模型类**: 对应的 Python ORM 模型类名
- **业务描述**: 从模型 Docstring 提取的业务用途说明
- **字段定义**: 包含字段名、类型、约束、可空性、默认值和业务说明
- **关系映射**: 表间的 ORM 关系（一对多、多对一等）

### 字段注释规范
- 所有新增字段必须在模型定义中使用 `comment` 参数添加业务说明
- 枚举类型字段需列出所有可选值
- 外键字段需说明关联的业务实体

---

## 数据表清单

本系统共包含 **{len(all_models)} 个数据表**，分为以下几个业务域：

"""

    # 生成表清单
    for domain_name, models_list in categories.items():
        if not models_list:
            continue
        md += f'\n### {domain_name}\n'
        for model in models_list:
            md += f'- `{model.__tablename__}` - {model.__name__}\n'

    md += '\n---\n\n'

    # 生成详细文档
    for domain_name, models_list in categories.items():
        if not models_list:
            continue

        md += f'## {domain_name}\n\n'

        for model in models_list:
            table_doc = generate_table_documentation(model)
            md += f"### {model.__name__} (`{table_doc['table_name']}`)\n\n"
            md += f"**业务描述**: {table_doc['description']}\n\n"
            md += '#### 字段定义\n\n'
            md += generate_markdown_table(table_doc['columns'])
            md += '\n'

            if table_doc['relationships']:
                md += '#### 关系映射\n\n'
                for rel in table_doc['relationships']:
                    md += f"- **{rel['name']}**: {rel['type']} -> `{rel['target']}`\n"
                md += '\n'

            md += '---\n\n'

    # 添加变更日志章节
    md += """
## 变更日志

### v2.2 (自动生成)
- 基于最新 SQLAlchemy 模型自动生成
- 支持变更检测和 Diff 对比
- 增强字段注释提取
- 优化默认值显示

---

**维护说明**: 本文档由 `scripts/generate_data_dictionary.py` 自动生成。
如需更新，请修改模型定义并运行 `make docs` 命令。
"""

    return md, table_names


def main():
    """主函数：生成并保存数据字典。"""
    print('=' * 60)
    print('Data Dictionary Generator v2.2')
    print('=' * 60)
    print(f'Scanning models from: devops_collector.models')

    try:
        output_path = Path(__file__).parent.parent / 'docs' / 'api' / 'DATA_DICTIONARY.md'
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 生成新版本
        markdown_content, new_tables = generate_full_data_dictionary()

        # 生成变更日志
        summary, changes = generate_changelog(output_path, new_tables)
        print(f'\nChange Summary: {summary}')
        for change in changes:
            print(f'  {change}')

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        print(f'\nData Dictionary generated successfully!')
        print(f'Output: {output_path}')
        print(f'Total tables documented: {len(new_tables)}')

    except Exception as e:
        print(f'\nError generating data dictionary: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
