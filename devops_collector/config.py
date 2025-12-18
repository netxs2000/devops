"""DevOps 数据采集服务配置模块

支持从 config.ini 文件和环境变量加载配置，优先级：
1. config.ini 文件
2. 环境变量
3. 默认值

使用方式:
    from devops_collector.config import Config
    print(Config.GITLAB_URL)
    print(Config.SONARQUBE_URL)
"""
import os
import configparser

# Load config from config.ini
config_parser = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
config_parser.read(config_path)

class Config:
    """配置类，聚合所有系统参数。
    
    分类：
    - GitLab: API 连接信息
    - Database: PostgreSQL 连接 URI
    - RabbitMQ: 消息队列连接信息
    - Analysis: 深度分析开关和忽略文件模式
    - Rate Limit: API 速率限制
    - Client: HTTP 客户端参数
    - Scheduler: 同步调度参数
    - Logging: 日志级别
    """
    # GitLab
    GITLAB_URL = config_parser.get('gitlab', 'url', fallback=os.getenv('GITLAB_URL', 'https://gitlab.com'))
    GITLAB_PRIVATE_TOKEN = config_parser.get('gitlab', 'private_token', fallback=os.getenv('GITLAB_PRIVATE_TOKEN', ''))
    
    # Database
    DB_URI = config_parser.get('database', 'uri', fallback=os.getenv('DB_URI', 'postgresql://gitlab_collector:password@localhost/gitlab_data'))
    
    # RabbitMQ
    RABBITMQ_HOST = config_parser.get('rabbitmq', 'host', fallback=os.getenv('RABBITMQ_HOST', 'rabbitmq'))
    RABBITMQ_QUEUE = config_parser.get('rabbitmq', 'queue', fallback=os.getenv('RABBITMQ_QUEUE', 'gitlab_tasks'))
    RABBITMQ_URL = os.getenv('RABBITMQ_URL', f'amqp://user:password@{RABBITMQ_HOST}:5672/')
    
    # Deep Analysis Configuration
    ENABLE_DEEP_ANALYSIS = config_parser.getboolean('analysis', 'enable_deep_analysis', fallback=os.getenv('ENABLE_DEEP_ANALYSIS', 'False').lower() == 'true')
    
    _patterns = config_parser.get('analysis', 'ignored_file_patterns', fallback='')
    if _patterns:
        IGNORED_FILE_PATTERNS = [p.strip() for p in _patterns.split(',') if p.strip()]
    else:
        # Fallback to default list if not in config
        IGNORED_FILE_PATTERNS = [
            '*.lock', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
            '*.min.js', '*.min.css', '*.map',
            'node_modules/*', 'dist/*', 'build/*', 'vendor/*',
            '*.svg', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.ico',
            '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx', '*.ppt', '*.pptx',
            '*.zip', '*.tar', '*.gz', '*.rar', '*.7z',
            '*.exe', '*.dll', '*.so', '*.dylib'
        ]
    
    # Rate Limiting
    REQUESTS_PER_SECOND = config_parser.getint('ratelimit', 'requests_per_second', fallback=int(os.getenv('REQUESTS_PER_SECOND', '10')))

    # Client
    CLIENT_TIMEOUT = config_parser.getint('client', 'timeout', fallback=10)
    CLIENT_PER_PAGE = config_parser.getint('client', 'per_page', fallback=100)
    CLIENT_MAX_RETRIES = config_parser.getint('client', 'max_retries', fallback=5)
    
    # Scheduler
    SYNC_INTERVAL_MINUTES = config_parser.getint('scheduler', 'sync_interval_minutes', fallback=10)
    
    # Logging
    LOG_LEVEL = config_parser.get('logging', 'level', fallback='INFO').upper()
    
    # ============================================
    # SonarQube Configuration (NEW)
    # ============================================
    SONARQUBE_URL = config_parser.get('sonarqube', 'url', fallback=os.getenv('SONARQUBE_URL', ''))
    SONARQUBE_TOKEN = config_parser.get('sonarqube', 'token', fallback=os.getenv('SONARQUBE_TOKEN', ''))
    SONARQUBE_SYNC_INTERVAL_HOURS = config_parser.getint('sonarqube', 'sync_interval_hours', fallback=24)
    SONARQUBE_SYNC_ISSUES = config_parser.getboolean('sonarqube', 'sync_issues', fallback=False)

    # ============================================
    # Jenkins Configuration (NEW)
    # ============================================
    JENKINS_URL = config_parser.get('jenkins', 'url', fallback=os.getenv('JENKINS_URL', ''))
    JENKINS_USER = config_parser.get('jenkins', 'user', fallback=os.getenv('JENKINS_USER', ''))
    JENKINS_TOKEN = config_parser.get('jenkins', 'token', fallback=os.getenv('JENKINS_TOKEN', ''))
    JENKINS_SYNC_INTERVAL_HOURS = config_parser.getint('jenkins', 'sync_interval_hours', fallback=12)
    JENKINS_BUILD_SYNC_LIMIT = config_parser.getint('jenkins', 'build_sync_limit', fallback=100)
