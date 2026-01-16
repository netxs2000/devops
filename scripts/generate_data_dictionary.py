"""数据字典自动生成器 (Data Dictionary Generator)

基于 SQLAlchemy 模型反射，自动生成企业级数据字典文档。

功能特性:
    - 自动扫描所有 ORM 模型
    - 提取表结构、字段类型、约束、关系
    - 生成 Markdown 格式的标准化文档
"""
import sys
import inspect
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy import inspect as sa_inspect
from devops_collector.models import Base
from devops_collector import models

def get_column_type_description(column) -> str:
    """获取列类型的友好描述
    
    Args:
        column: SQLAlchemy Column 对象
    
    Returns:
        str: 类型描述字符串（如 "String(200)"）
    """
    col_type = str(column.type)
    if 'VARCHAR' in col_type:
        return col_type.replace('VARCHAR', 'String')
    elif 'INTEGER' in col_type:
        return 'Integer'
    elif 'BOOLEAN' in col_type:
        return 'Boolean'
    elif 'DATETIME' in col_type:
        return 'DateTime'
    elif 'UUID' in col_type:
        return 'UUID'
    elif 'JSONB' in col_type:
        return 'JSONB'
    elif 'FLOAT' in col_type or 'NUMERIC' in col_type:
        return 'Numeric'
    elif 'TEXT' in col_type:
        return 'Text'
    elif 'BIGINT' in col_type:
        return 'BigInteger'
    else:
        return col_type

def get_column_constraints(column) -> List[str]:
    """获取列的约束信息
    
    Args:
        column: SQLAlchemy Column 对象
    
    Returns:
        List[str]: 约束列表（如 ['PK', 'NOT NULL']）
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
    """从模型类的 docstring 提取业务描述
    
    Args:
        model_class: SQLAlchemy 模型类
    
    Returns:
        str: 业务描述文本
    """
    doc = inspect.getdoc(model_class)
    if not doc:
        return '无描述'
    lines = doc.split('\n')
    description = []
    for line in lines:
        line = line.strip()
        if line and (not line.startswith('Attributes:')) and (not line.startswith('Args:')):
            description.append(line)
        elif line.startswith('Attributes:'):
            break
    return ' '.join(description) if description else '无描述'

def generate_table_documentation(model_class) -> Dict[str, Any]:
    """为单个模型生成表文档
    
    Args:
        model_class: SQLAlchemy 模型类
    
    Returns:
        Dict[str, Any]: 包含表信息的字典
    """
    mapper = sa_inspect(model_class)
    table_name = model_class.__tablename__
    description = extract_docstring_description(model_class)
    columns_info = []
    for column in mapper.columns:
        col_info = {'name': column.name, 'type': get_column_type_description(column), 'constraints': get_column_constraints(column), 'nullable': column.nullable, 'default': str(column.default.arg) if column.default else '-', 'comment': column.comment or '-'}
        columns_info.append(col_info)
    relationships_info = []
    for rel_name, rel in mapper.relationships.items():
        relationships_info.append({'name': rel_name, 'target': rel.mapper.class_.__name__, 'type': 'one-to-many' if rel.uselist else 'many-to-one'})
    return {'table_name': table_name, 'model_class': model_class.__name__, 'description': description, 'columns': columns_info, 'relationships': relationships_info}

def generate_markdown_table(columns_info: List[Dict]) -> str:
    """生成 Markdown 格式的表格
    
    Args:
        columns_info: 列信息列表
    
    Returns:
        str: Markdown 表格字符串
    """
    md = '| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |\n'
    md += '|:-------|:---------|:-----|:-----|:-------|:-----|\n'
    for col in columns_info:
        constraints_str = ', '.join(col['constraints']) if col['constraints'] else '-'
        nullable_str = '是' if col['nullable'] else '否'
        md += f"| `{col['name']}` | {col['type']} | {constraints_str} | {nullable_str} | {col['default']} | {col['comment']} |\n"
    return md

def generate_full_data_dictionary() -> str:
    """生成完整的数据字典文档
    
    Returns:
        str: 完整的 Markdown 格式数据字典
    """
    all_models = []
    for name, obj in inspect.getmembers(models):
        if inspect.isclass(obj) and hasattr(obj, '__tablename__') and (obj != Base):
            all_models.append(obj)
    all_models.sort(key=lambda m: m.__tablename__)
    md = f"# DevOps 效能平台 - 数据字典 (Data Dictionary)\n\n> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n> **版本**: v2.1 (企业级标准版)  \n> **状态**: 有效 (Active)\n\n---\n\n## 文档说明\n\n本数据字典基于系统最新的 SQLAlchemy ORM 模型自动生成，确保与实际数据库结构的一致性。\n\n### 文档结构\n- **表名**: 数据库表的物理名称\n- **模型类**: 对应的 Python ORM 模型类名\n- **业务描述**: 从模型 Docstring 提取的业务用途说明\n- **字段定义**: 包含字段名、类型、约束、可空性、默认值和业务说明\n- **关系映射**: 表间的 ORM 关系（一对多、多对一等）\n\n---\n\n## 数据表清单\n\n本系统共包含 **{len(all_models)} 个数据表**，分为以下几个业务域：\n\n"
    core_tables = []
    gitlab_tables = []
    test_tables = []
    auth_tables = []
    analytics_tables = []
    other_tables = []
    for model in all_models:
        table_name = model.__tablename__
        if 'mdm_' in table_name or table_name in ['organizations', 'products', 'services']:
            core_tables.append(model)
        elif 'gitlab_' in table_name or table_name in ['sync_logs']:
            gitlab_tables.append(model)
        elif 'test_' in table_name or 'requirement' in table_name:
            test_tables.append(model)
        elif 'auth_' in table_name or 'credential' in table_name:
            auth_tables.append(model)
        elif 'view_' in table_name or 'okr_' in table_name:
            analytics_tables.append(model)
        else:
            other_tables.append(model)
    if core_tables:
        md += '\n### 核心主数据域 (Core Master Data)\n'
        for model in core_tables:
            md += f'- `{model.__tablename__}` - {model.__name__}\n'
    if test_tables:
        md += '\n### 测试管理域 (Test Management)\n'
        for model in test_tables:
            md += f'- `{model.__tablename__}` - {model.__name__}\n'
    if gitlab_tables:
        md += '\n### GitLab 集成域 (GitLab Integration)\n'
        for model in gitlab_tables:
            md += f'- `{model.__tablename__}` - {model.__name__}\n'
    if auth_tables:
        md += '\n### 认证与授权域 (Authentication & Authorization)\n'
        for model in auth_tables:
            md += f'- `{model.__tablename__}` - {model.__name__}\n'
    if analytics_tables:
        md += '\n### 分析与洞察域 (Analytics & Insights)\n'
        for model in analytics_tables:
            md += f'- `{model.__tablename__}` - {model.__name__}\n'
    if other_tables:
        md += '\n### 其他辅助域 (Other Supporting Tables)\n'
        for model in other_tables:
            md += f'- `{model.__tablename__}` - {model.__name__}\n'
    md += '\n---\n\n'
    all_tables_grouped = [('核心主数据域', core_tables), ('测试管理域', test_tables), ('GitLab 集成域', gitlab_tables), ('认证与授权域', auth_tables), ('分析与洞察域', analytics_tables), ('其他辅助域', other_tables)]
    for domain_name, models_list in all_tables_grouped:
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
                    md += f"- **{rel['name']}**: {rel['type']} → `{rel['target']}`\n"
                md += '\n'
            md += '---\n\n'
    md += f'\n## 变更日志\n\n### v2.1 (2025-01-16)\n- 基于最新 SQLAlchemy 模型自动生成\n- 移除所有表情符号以符合规范\n- 新增企业级分域架构组织\n- 完善字段约束和关系映射说明\n\n---\n\n**维护说明**: 本文档由 `scripts/generate_data_dictionary.py` 自动生成，请勿手动编辑！如需更新，请修改模型定义并重新运行生成脚本。\n'
    return md

def main():
    """主函数：生成并保存数据字典"""
    print('Starting Data Dictionary Generation...')
    print(f'Scanning models from: devops_collector.models')
    try:
        markdown_content = generate_full_data_dictionary()
        output_path = Path(__file__).parent.parent / 'docs' / 'api' / 'DATA_DICTIONARY.md'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f'\nData Dictionary generated successfully!')
        print(f'Output: {output_path}')
        print(f"Total tables documented: {markdown_content.count('###') - markdown_content.count('####')}")
    except Exception as e:
        print(f'\nError generating data dictionary: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
if __name__ == '__main__':
    main()
