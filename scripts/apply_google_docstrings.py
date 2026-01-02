import ast
import os
from pathlib import Path

MODULE_PLACEHOLDER = """TODO: Add module description."""
PLACEHOLDER = '''"""TODO: Add description.

Args:
    {args}

Returns:
    TODO

Raises:
    TODO
"""'''

def format_args(args):
    if not args:
        return 'TODO'
    return '\n    '.join([f"{a}: TODO" for a in args])

class DocstringInserter(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if not (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)):
            args = [arg.arg for arg in node.args.args]
            placeholder = PLACEHOLDER.format(args=format_args(args))
            doc_node = ast.Expr(value=ast.Constant(value=placeholder))
            node.body.insert(0, doc_node)
        return node

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        if not (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)):
            placeholder = '"""TODO: Add class description."""'
            doc_node = ast.Expr(value=ast.Constant(value=placeholder))
            node.body.insert(0, doc_node)
        return node

def process_file(file_path: Path):
    try:
        source = file_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        # Insert module docstring if missing
        if not (tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant)):
            module_doc = ast.Expr(value=ast.Constant(value=MODULE_PLACEHOLDER))
            tree.body.insert(0, module_doc)
        inserter = DocstringInserter()
        new_tree = inserter.visit(tree)
        ast.fix_missing_locations(new_tree)
        new_source = ast.unparse(new_tree)
        file_path.write_text(new_source, encoding='utf-8')
        print(f"Processed {file_path}")
    except Exception as e:
        print(f"Failed {file_path}: {e}")

def main():
    root = Path(__file__).parents[2]  # project root (devops)
    for py_file in root.rglob('*.py'):
        if any(part.startswith('.') for part in py_file.parts):
            continue
        if py_file.name == 'apply_google_docstrings.py':
            continue
        process_file(py_file)

if __name__ == '__main__':
    main()
