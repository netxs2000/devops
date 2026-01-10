"""
Dashboard 页面自动化健康检查脚本

该脚本通过直接执行每个页面的 SQL 查询来验证数据仓库表和列是否存在，
可快速识别 column/table does not exist 等常见错误。

Usage:
    # 本地运行
    python scripts/test_dashboard_pages.py

    # 容器内运行
    docker-compose exec -T api python scripts/test_dashboard_pages.py
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, OperationalError
from devops_collector.config import settings


class DashboardPageTester:
    """Dashboard 页面健康检查器。

    该类扫描所有仪表盘页面文件，提取 SQL 查询并验证其是否可执行。
    """

    def __init__(self):
        """初始化测试器。"""
        self.engine = create_engine(settings.database.uri)
        self.dashboard_dir = Path(__file__).parent.parent / "dashboard" / "pages"
        self.results = []

    def extract_sql_queries(self, content: str) -> list[tuple[str, str]]:
        """从 Python 文件内容中提取 SQL 查询。

        Args:
            content: Python 文件内容

        Returns:
            包含 (查询名称, SQL语句) 元组的列表
        """
        queries = []

        # 匹配多行字符串中的 SQL (run_query 调用)
        pattern = r'run_query\s*\(\s*["\']+(.*?)["\']+\s*\)'
        matches = re.findall(pattern, content, re.DOTALL)

        for i, sql in enumerate(matches):
            # 清理 SQL
            sql = sql.strip()
            if sql:
                queries.append((f"Query_{i+1}", sql))

        # 匹配三引号字符串中的 SQL
        triple_pattern = r'run_query\s*\(\s*"""(.*?)"""\s*\)'
        triple_matches = re.findall(triple_pattern, content, re.DOTALL)

        for i, sql in enumerate(triple_matches):
            sql = sql.strip()
            if sql:
                queries.append((f"TripleQuery_{i+1}", sql))

        return queries

    def test_sql_query(self, sql: str, page_name: str, query_name: str) -> dict:
        """测试单个 SQL 查询是否可执行。

        Args:
            sql: SQL 查询语句
            page_name: 页面名称
            query_name: 查询名称

        Returns:
            测试结果字典
        """
        result = {
            "page": page_name,
            "query": query_name,
            "sql": sql[:100] + "..." if len(sql) > 100 else sql,
            "status": "PASS",
            "error": None
        }

        try:
            with self.engine.connect() as conn:
                # 使用 EXPLAIN 来验证 SQL 结构而不实际执行
                # 对于简单查询，直接用 LIMIT 1 执行
                test_sql = sql.strip()
                if not test_sql.upper().startswith("EXPLAIN"):
                    # 添加 LIMIT 1 来限制结果
                    if "LIMIT" not in test_sql.upper():
                        test_sql = f"SELECT * FROM ({test_sql}) AS _test_wrapper LIMIT 1"
                    else:
                        test_sql = test_sql

                conn.execute(text(test_sql))
                conn.commit()

        except ProgrammingError as e:
            result["status"] = "FAIL"
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            result["error"] = error_msg

        except OperationalError as e:
            result["status"] = "FAIL"
            result["error"] = f"数据库连接错误: {e}"

        except Exception as e:
            result["status"] = "WARN"
            result["error"] = f"未知错误: {e}"

        return result

    def test_page(self, page_path: Path) -> list[dict]:
        """测试单个页面文件中的所有 SQL 查询。

        Args:
            page_path: 页面文件路径

        Returns:
            该页面所有查询的测试结果列表
        """
        page_name = page_path.stem
        results = []

        try:
            content = page_path.read_text(encoding="utf-8")
        except Exception as e:
            return [{
                "page": page_name,
                "query": "N/A",
                "sql": "N/A",
                "status": "ERROR",
                "error": f"无法读取文件: {e}"
            }]

        queries = self.extract_sql_queries(content)

        if not queries:
            return [{
                "page": page_name,
                "query": "N/A",
                "sql": "N/A",
                "status": "SKIP",
                "error": "未检测到 SQL 查询"
            }]

        for query_name, sql in queries:
            result = self.test_sql_query(sql, page_name, query_name)
            results.append(result)

        return results

    def run_all_tests(self) -> list[dict]:
        """运行所有页面的测试。

        Returns:
            所有测试结果列表
        """
        all_results = []

        if not self.dashboard_dir.exists():
            print(f"[ERROR] Dashboard 目录不存在: {self.dashboard_dir}")
            return all_results

        page_files = sorted(self.dashboard_dir.glob("*.py"))

        print("=" * 70)
        print("Dashboard 页面健康检查")
        print("=" * 70)
        print(f"发现 {len(page_files)} 个页面文件")
        print("-" * 70)

        for page_path in page_files:
            results = self.test_page(page_path)
            all_results.extend(results)

            for r in results:
                status_icon = {
                    "PASS": "[OK]",
                    "FAIL": "[FAIL]",
                    "WARN": "[WARN]",
                    "SKIP": "[SKIP]",
                    "ERROR": "[ERROR]"
                }.get(r["status"], "[?]")

                print(f"{status_icon} {r['page']}: {r['query']}")
                if r["error"]:
                    # 只显示错误的关键信息
                    error_short = r["error"][:200] if len(r["error"]) > 200 else r["error"]
                    print(f"       -> {error_short}")

        return all_results

    def print_summary(self, results: list[dict]) -> int:
        """打印测试摘要。

        Args:
            results: 测试结果列表

        Returns:
            失败的测试数量
        """
        print("\n" + "=" * 70)
        print("测试摘要")
        print("=" * 70)

        pass_count = sum(1 for r in results if r["status"] == "PASS")
        fail_count = sum(1 for r in results if r["status"] == "FAIL")
        warn_count = sum(1 for r in results if r["status"] == "WARN")
        skip_count = sum(1 for r in results if r["status"] == "SKIP")

        print(f"  PASS:  {pass_count}")
        print(f"  FAIL:  {fail_count}")
        print(f"  WARN:  {warn_count}")
        print(f"  SKIP:  {skip_count}")
        print(f"  TOTAL: {len(results)}")

        if fail_count > 0:
            print("\n" + "-" * 70)
            print("失败详情:")
            for r in results:
                if r["status"] == "FAIL":
                    print(f"\n  Page: {r['page']}")
                    print(f"  Query: {r['query']}")
                    print(f"  SQL: {r['sql']}")
                    print(f"  Error: {r['error']}")

        return fail_count


def main():
    """主入口函数。"""
    tester = DashboardPageTester()
    results = tester.run_all_tests()
    fail_count = tester.print_summary(results)

    # 返回失败数量作为退出码
    sys.exit(min(fail_count, 1))


if __name__ == "__main__":
    main()
