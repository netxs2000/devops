import ast
import glob
import os
import re
import sys
import pandas as pd
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.append(os.getcwd())

from devops_collector.config import settings

def get_db_engine():
    # Force localhost for script execution outside docker
    uri = settings.database.uri.replace('@db:', '@localhost:')
    return create_engine(uri)

def extract_sql_queries(file_path):
    print(f"Scanning {os.path.basename(file_path)}...")
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    queries = []
    
    class QueryVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            # Check for run_query(...) calls
            if isinstance(node.func, ast.Name) and node.func.id == 'run_query':
                if node.args:
                    arg = node.args[0]
                    self._process_arg(arg)
            # Check for pd.read_sql(...) calls
            elif isinstance(node.func, ast.Attribute) and node.func.attr == 'read_sql':
                if node.args:
                    arg = node.args[0]
                    self._process_arg(arg)
            
            self.generic_visit(node)

        def _process_arg(self, arg):
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                queries.append({"type": "static", "sql": arg.value})
            elif isinstance(arg, ast.JoinedStr):
                # Handle f-strings: try to reconstruct, replacing {} with placeholders or ignoring
                # This is a best-effort heuristic
                raw_sql = ""
                is_valid = True
                for part in arg.values:
                    if isinstance(part, ast.Constant):
                        raw_sql += part.value
                    elif isinstance(part, ast.FormattedValue):
                        # Replace variable interpolation with a dummy 0 or 'dummy' 
                        # This is risky but often works for LIMIT {x} or similar.
                        # For WHERE clauses it might break syntax.
                        # Let's try to be smart: if it looks like a number, use 1.
                        raw_sql += "NULL" # safest for values, bad for syntax literals
                queries.append({"type": "dynamic", "sql": raw_sql, "raw_node": arg})
            elif isinstance(arg, ast.Name):
                 queries.append({"type": "variable", "name": arg.id})

    QueryVisitor().visit(tree)
    return queries

def validate_query(engine, sql):
    # Try to EXPLAIN the query to check validity without running it fully
    # Or just run with LIMIT 0
    
    # Clean up common f-string artifacts if we can
    # e.g. "SELECT * FROM table LIMIT NULL" might fail syntax
    
    # For now, simplistic check: valid SQL?
    try:
        # We wrap in a transaction that rolls back
        with engine.connect() as conn:
            # We add LIMIT 0 to avoid fetching data, but wrapping valid SQL is hard if it already has limit
            # Just try to prepare it.
            
            # Heuristic: if dynamic, we might skip or warn
            if "NULL" in sql: 
               # Simple f-string reconstruction often produces invalid SQL (e.g. LIMIT NULL)
               # user provided queries often use {limit}.
               # Let's replace NULL with 1 for likely integer spots
               temp_sql = sql.replace("LIMIT NULL", "LIMIT 1")
               
               # If it was IN ({...}) -> IN (NULL) -> might be valid?
               # Let's try running it
               conn.execute(text(temp_sql))
            else:
               conn.execute(text(f"EXPLAIN {sql}"))
            
            return True, None
    except Exception as e:
        return False, str(e)

def search_tables_in_query(sql):
    # Regex to find table names: FROM x or JOIN x
    # Matches: public_marts.xxx or public_intermediate.xxx
    tables = re.findall(r'(?:FROM|JOIN)\s+(public_[a-z_]+\.[a-z0-9_]+)', sql, re.IGNORECASE)
    return set(tables)

def check_table_exists(engine, table_name):
    schema, table = table_name.split('.')
    try:
        with engine.connect() as conn:
            res = conn.execute(text(f"SELECT 1 FROM information_schema.tables WHERE table_schema = '{schema}' AND table_name = '{table}'"))
            return res.scalar() is not None
    except:
        return False

def main():
    engine = get_db_engine()
    pages_dir = os.path.join("dashboard", "pages")
    results = []

    print(f"Scanning dashboard pages in {pages_dir}...")
    
    files = glob.glob(os.path.join(pages_dir, "*.py"))
    
    for file_path in files:
        filename = os.path.basename(file_path)
        queries = extract_sql_queries(file_path)
        
        for q in queries:
            status = "UNKNOWN"
            error = None
            
            if q['type'] == 'static':
                valid, err = validate_query(engine, q['sql'])
                if valid:
                    status = "PASS"
                else:
                    status = "FAIL"
                    error = err
            elif q['type'] == 'dynamic':
                # For dynamic queries, at least check if the referenced tables exist
                # This catches 'relation does not exist' errors which are common
                tables = search_tables_in_query(q['sql'])
                missing_tables = []
                for t in tables:
                    if not check_table_exists(engine, t):
                        missing_tables.append(t)
                
                if missing_tables:
                    status = "FAIL"
                    error = f"Missing tables: {', '.join(missing_tables)}"
                else:
                    status = "WARN (Dynamic)"
                    error = "Dynamic query detected - verify logic manually"
            
            results.append({
                "page": filename,
                "type": q['type'],
                "status": status,
                "error": error,
                "sql_snippet": q.get('sql', 'N/A')[:50] + "..."
            })

    # Report
    print("\n" + "="*80)
    print("DASHBOARD SQL INTEGRITY REPORT")
    print("="*80)
    
    df = pd.DataFrame(results)
    if not df.empty:
        # Group by Status
        for status in df['status'].unique():
            print(f"\n--- {status} ---")
            subset = df[df['status'] == status]
            for _, row in subset.iterrows():
                print(f"[{row['page']}] {row['type']}: {row['sql_snippet']}")
                if row['error']:
                    print(f"    ❌ ERROR: {row['error']}")
    else:
        print("No SQL queries found via static analysis.")

if __name__ == "__main__":
    main()
