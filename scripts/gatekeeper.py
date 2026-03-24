import argparse
import subprocess
import sys
import time


# 定义 ANSI 颜色
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def run_command(command, description):
    print(f"\n{CYAN}>>> [{description}] Executing: {command}{RESET}")
    start_time = time.time()

    try:
        # 强制使用 UTF-8 编码读取输出，并对错误字节进行替换，防止 GBK 解码失败
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            universal_newlines=True,
        )

        # 实时打印输出流
        if process.stdout is not None:
            for line in process.stdout:
                print(line, end="")

        process.wait()
        duration = time.time() - start_time

        if process.returncode == 0:
            print(f"{GREEN}[V] [{description}] PASSED ({duration:.1f}s){RESET}")
            return True
        else:
            print(f"{RED}[X] [{description}] FAILED (Exit code: {process.returncode}){RESET}")
            return False

    except Exception as e:
        # 使用 ASCII 兼容的错误输出
        print(f"{RED}[X] [{description}] ERROR: {str(e)}{RESET}")
        return False


def main():
    # 强制设置控制台输出为 UTF-8 (Python 3.7+)
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            import io

            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="DevOps Platform Full Gate (Pre-merge Check)")
    parser.add_argument("--mode", choices=["fast", "full"], default="full", help="Check mode (fast: skip build, full: all checks)")
    args = parser.parse_args()

    print(f"{YELLOW}====================================================================")
    print(f"        DevOps Platform Full Gate Check - Mode: {args.mode.upper()}        ")
    print(f"===================================================================={RESET}")

    overall_start = time.time()

    # 阶段 1: Linting (L1)
    if not run_command("make lint", "L1: Linting & Style Check"):
        sys.exit(1)

    # 阶段 2: Testing (L2 - Containerized)
    if not run_command("make test", "L2: All Tests (Unit + Integration)"):
        sys.exit(1)

    # 阶段 3: Building (L3 - Full Mode only)
    if args.mode == "full":
        if not run_command("make build", "L3: Docker Image Build & Cache Verification"):
            sys.exit(1)

        # 可选：阶段 4: 冒烟测试
        # if not run_command("make test-smoke", "L4: Smoke Test (Containerized)"):
        #     sys.exit(1)

    overall_duration = time.time() - overall_start
    print(f"\n{GREEN}====================================================================")
    print(f"        SUCCESS: FULL GATE PASSED ({overall_duration:.1f}s)            ")
    print("        Your code is now ready for merge/deployment.                ")
    print(f"===================================================================={RESET}")


if __name__ == "__main__":
    main()
