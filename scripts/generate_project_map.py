import os


def generate_map(root_dir):
    """生成项目核心目录拓扑图，并标注核心职责。"""

    # 核心文件夹扫描白名单
    scan_dirs = ["devops_collector", "tests/unit/devops_collector", "devops_portal", "infrastructure/scripts"]
    output_file = os.path.join(root_dir, "docs/PROJECT_MAP.md")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# DevOps Platform 系统资源清单 (PROJECT_MAP.md)\n\n")
        f.write("> **定位**：本文件为 AI 助手（及开发者）提供全局资源导航。在寻找 Client, Worker, Test, Model 时优先读取本图谱。\n\n")

        for base_dir in scan_dirs:
            full_path = os.path.join(root_dir, base_dir)
            if not os.path.exists(full_path):
                continue

            f.write(f"## {base_dir}\n")
            f.write("```text\n")

            # 使用简单的树结构遍历
            for root, dirs, files in os.walk(full_path):
                # 排除缓存和内部目录
                dirs[:] = [d for d in dirs if d not in ["__pycache__", ".venv", ".pytest_cache"]]

                level = root.replace(full_path, "").count(os.sep)
                indent = "  " * level
                folder_name = os.path.basename(root)
                f.write(f"{indent}{folder_name}/\n")

                sub_indent = "  " * (level + 1)
                for file in files:
                    if file.endswith((".py", ".sh", ".sql", ".md")) and "__init__" not in file:
                        # 核心职责标注逻辑
                        role = ""
                        if "client" in file:
                            role = " [⚡ CLIENT: API Connection]"
                        elif "worker" in file:
                            role = " [⚙️ WORKER: Business Orchestration]"
                        elif "service" in file:
                            role = " [🛠️ SERVICE: Data Logic]"
                        elif "models" in file:
                            role = " [📄 MODELS: Schema]"
                        elif "test_" in file:
                            role = " [🚀 TEST: Unit Protection]"

                        f.write(f"{sub_indent}{file}{role}\n")

            f.write("```\n\n")

    print(f"Project Map generated successfully at: {output_file}")


if __name__ == "__main__":
    current_root = os.getcwd()
    generate_map(current_root)
