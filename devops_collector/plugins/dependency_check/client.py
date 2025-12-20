"""
OWASP Dependency-Check Client
封装 OWASP Dependency-Check CLI 调用
"""
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional


class DependencyCheckClient:
    """OWASP Dependency-Check CLI 客户端"""
    
    def __init__(self, cli_path: str = 'dependency-check', timeout: int = 600):
        """
        初始化客户端
        
        Args:
            cli_path: Dependency-Check CLI 路径
            timeout: 扫描超时时间（秒）
        """
        self.cli_path = cli_path
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
    
    def scan_project(
        self, 
        project_path: str, 
        output_dir: str,
        project_name: Optional[str] = None,
        scan_transitive: bool = True
    ) -> str:
        """
        扫描项目依赖
        
        Args:
            project_path: 项目本地路径
            output_dir: 报告输出目录
            project_name: 项目名称
            scan_transitive: 是否扫描传递依赖
            
        Returns:
            报告文件路径
            
        Raises:
            RuntimeError: 扫描失败
            FileNotFoundError: 报告文件不存在
        """
        # 确保输出目录存在
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 构建命令
        cmd = [
            self.cli_path,
            '--scan', project_path,
            '--format', 'JSON',
            '--out', str(output_path),
            '--prettyPrint',
        ]
        
        if project_name:
            cmd.extend(['--project', project_name])
        
        if scan_transitive:
            cmd.append('--enableExperimental')
        
        # 禁用自动更新（生产环境）
        cmd.append('--noupdate')
        
        self.logger.info(f"Running Dependency-Check: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                timeout=self.timeout,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Dependency-Check 即使发现漏洞也会返回 0
            # 只有在严重错误时才会返回非 0
            if result.returncode != 0:
                self.logger.error(f"Dependency-Check failed: {result.stderr}")
                raise RuntimeError(f"Dependency-Check failed with code {result.returncode}: {result.stderr}")
            
            # 查找报告文件
            report_path = output_path / "dependency-check-report.json"
            if not report_path.exists():
                raise FileNotFoundError(f"Report not found: {report_path}")
            
            self.logger.info(f"Scan completed successfully. Report: {report_path}")
            return str(report_path)
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Scan timeout after {self.timeout} seconds")
            raise RuntimeError(f"Scan timeout after {self.timeout} seconds")
        except Exception as e:
            self.logger.error(f"Scan failed: {e}")
            raise
    
    def parse_report(self, report_path: str) -> Dict:
        """
        解析 JSON 报告
        
        Args:
            report_path: 报告文件路径
            
        Returns:
            解析后的报告数据
        """
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to parse report {report_path}: {e}")
            raise
    
    def get_version(self) -> Optional[str]:
        """
        获取 Dependency-Check 版本
        
        Returns:
            版本号字符串
        """
        try:
            result = subprocess.run(
                [self.cli_path, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # 解析版本号（格式: "Dependency-Check Core version 8.4.0")
                output = result.stdout.strip()
                if 'version' in output.lower():
                    version = output.split('version')[-1].strip()
                    return version
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to get Dependency-Check version: {e}")
            return None
