import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from devops_collector.plugins.nexus.client import NexusClient
from devops_collector.plugins.nexus.config import get_config


logging.basicConfig(level=logging.ERROR)


def analyze_nexus_lifecycle():
    config = get_config()["client"]
    client = NexusClient(url=config["url"], user=config["user"], password=config["password"], rate_limit=50)

    now = datetime.now(timezone.utc)
    periods = {
        "7_days": timedelta(days=7),
        "30_days": timedelta(days=30),
        "90_days": timedelta(days=90),
        "180_days": timedelta(days=180),
        "365_days": timedelta(days=365),
    }

    report = {}

    # 为了避免公网代理仓库（如 maven-central）中存在数百万依赖导致统计脚本挂起，
    # 我们为每个仓库设置抽样分析上限。如果需要全量，建议直接执行 DevOps 采集任务落库后通过 SQL 查询。
    MAX_COMPONENTS_PER_REPO = 100

    try:
        repos = client.list_repositories()
        total_repos = len(repos)
        print(f"Start analyzing {total_repos} Nexus repositories (Max {MAX_COMPONENTS_PER_REPO} components per repo for performance)...")

        for repo in repos:
            repo_name = repo["name"]
            repo_type = repo["type"]  # hosted, proxy, group
            repo_format = repo["format"]  # maven2, pypi, docker, raw

            if repo_type == "group":
                continue  # Skip groups to avoid double counting

            print(f"Scanning [{repo_type}] {repo_name} ({repo_format})...")

            repo_stats = {
                "format": repo_format,
                "type": repo_type,
                "total_components": 0,
                "total_assets": 0,
                "total_size_mb": 0.0,
                # Download activity (when developers pull from Nexus)
                "never_downloaded": 0,
                "download_last_7_days": 0,
                "download_last_30_days": 0,
                "download_last_90_days": 0,
                "download_last_180_days": 0,
                "download_older_than_180_days": 0,
                # Internet pull activity (when Nexus proxies from upstream)
                "pulled_from_internet_7_days": 0,
                "pulled_from_internet_30_days": 0,
                "pulled_from_internet_90_days": 0,
            }

            for comp in client.list_components(repo_name):
                repo_stats["total_components"] += 1
                assets = comp.get("assets", [])

                comp_size = 0
                last_download = None
                last_modified = None

                for a in assets:
                    repo_stats["total_assets"] += 1
                    comp_size += a.get("fileSize", 0)

                    # Parse dates
                    dl_str = a.get("lastDownloaded")
                    mod_str = a.get("lastModified")

                    if dl_str:
                        try:
                            dt = datetime.fromisoformat(dl_str.replace("Z", "+00:00"))
                            if last_download is None or dt > last_download:
                                last_download = dt
                        except:
                            pass

                    if mod_str:
                        try:
                            dt = datetime.fromisoformat(mod_str.replace("Z", "+00:00"))
                            if last_modified is None or dt > last_modified:
                                last_modified = dt
                        except:
                            pass

                repo_stats["total_size_mb"] += comp_size / (1024 * 1024)

                # Classify Downloads
                if not last_download:
                    repo_stats["never_downloaded"] += 1
                else:
                    age = now - last_download
                    if age <= periods["7_days"]:
                        repo_stats["download_last_7_days"] += 1
                        repo_stats["download_last_30_days"] += 1
                        repo_stats["download_last_90_days"] += 1
                        repo_stats["download_last_180_days"] += 1
                    elif age <= periods["30_days"]:
                        repo_stats["download_last_30_days"] += 1
                        repo_stats["download_last_90_days"] += 1
                        repo_stats["download_last_180_days"] += 1
                    elif age <= periods["90_days"]:
                        repo_stats["download_last_90_days"] += 1
                        repo_stats["download_last_180_days"] += 1
                    elif age <= periods["180_days"]:
                        repo_stats["download_last_180_days"] += 1
                    else:
                        repo_stats["download_older_than_180_days"] += 1

                # Classify upstream Pulls (For Proxies)
                if repo_type == "proxy" and last_modified:
                    age_mod = now - last_modified
                    if age_mod <= periods["7_days"]:
                        repo_stats["pulled_from_internet_7_days"] += 1
                        repo_stats["pulled_from_internet_30_days"] += 1
                        repo_stats["pulled_from_internet_90_days"] += 1
                    elif age_mod <= periods["30_days"]:
                        repo_stats["pulled_from_internet_30_days"] += 1
                        repo_stats["pulled_from_internet_90_days"] += 1
                    elif age_mod <= periods["90_days"]:
                        repo_stats["pulled_from_internet_90_days"] += 1

                if repo_stats["total_components"] >= MAX_COMPONENTS_PER_REPO:
                    print(f"  -> Reached sampling limit of {MAX_COMPONENTS_PER_REPO} for repository {repo_name}.")
                    break

            report[repo_name] = repo_stats

        # ------------------- Print Report -------------------
        print("\n\n" + "=" * 80)
        print("                 NEXUS LIFECYCLE STATISTICS REPORT (SAMPLING MODE)")
        print("=" * 80)

        for r_name, stats in report.items():
            print(f"\n[{stats['type'].upper()} / {stats['format'].upper()}] {r_name}")
            print(f"  • Components Scanned: {stats['total_components']}  |  Assets: {stats['total_assets']}  |  Total Size: {stats['total_size_mb']:.2f} MB")

            if stats["total_components"] == 0:
                continue

            print(f"  • Developer Pull Activity (Downloaded to Local):")
            print(f"    - Last 7 days   : {stats['download_last_7_days']}")
            print(f"    - Last 30 days  : {stats['download_last_30_days']}")
            print(f"    - Last 90 days  : {stats['download_last_90_days']}")
            print(f"    - Last 180 days : {stats['download_last_180_days']}")
            print(f"    - Dormant (>180d): {stats['download_older_than_180_days']}")
            print(f"    - NEVER Pulled  : {stats['never_downloaded']} (Cached but never used / Uploaded but unused)")

            if stats["type"] == "proxy":
                print(f"  • Upstream Pull Activity (Fetched from Internet to Nexus):")
                print(f"    - Last 7 days   : {stats['pulled_from_internet_7_days']}")
                print(f"    - Last 30 days  : {stats['pulled_from_internet_30_days']}")
                print(f"    - Last 90 days  : {stats['pulled_from_internet_90_days']}")

    except Exception as e:
        print(f"Error during analysis: {e}")


if __name__ == "__main__":
    analyze_nexus_lifecycle()
