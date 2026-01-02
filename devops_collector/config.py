"""DevOps 数据采集服务配置模块 (Pydantic V2 版)

采用 pydantic-settings 实现强类型配置管理，支持：
1. 从 config.ini 自动加载 (保持向下兼容)
2. 环境变量覆盖 (高优先级)
3. 自动类型转换与校验

使用方式:
    from devops_collector.config import settings
    print(settings.gitlab.url)
"""
import os
from typing import List, Optional
from pydantic import Field, HttpUrl, RedisDsn, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import configparser
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'config.ini')

class GitLabSettings(BaseSettings):
    """GitLab connection settings.

    Attributes:
        url (str): The base URL of the GitLab instance.
        private_token (str): The private access token for authentication (System-level).
        client_id (str): OAuth2 Application ID.
        client_secret (str): OAuth2 Application Secret.
        redirect_uri (str): OAuth2 Callback URL (e.g., http://portal/auth/callback).
    """
    url: str = 'https://gitlab.com'
    private_token: str = ''
    client_id: str = ''
    client_secret: str = ''
    redirect_uri: str = ''

class DatabaseSettings(BaseSettings):
    """Database connection and retention settings.

    Attributes:
        uri (str): The database connection URI (e.g., postgresql://user:pass@host/db).
        raw_data_retention_days (int): The number of days to retain raw data.
    """
    uri: str = 'postgresql://gitlab_collector:password@localhost/gitlab_data'
    raw_data_retention_days: int = 30

class RabbitMQSettings(BaseSettings):
    """RabbitMQ connection settings.

    Attributes:
        host (str): The RabbitMQ server host.
        queue (str): The default queue name.
        user (str): The username for authentication.
        password (str): The password for authentication.
    """
    host: str = 'rabbitmq'
    queue: str = 'gitlab_tasks'
    user: str = 'user'
    password: str = 'password'

    @property
    def url(self) -> str:
        """Constructs the AMQP URL from settings.

        Returns:
            str: The full AMQP connection string.
        """
        return f'amqp://{self.user}:{self.password}@{self.host}:5672/'

class AnalysisSettings(BaseSettings):
    """Code analysis configuration.

    Attributes:
        enable_deep_analysis (bool): Whether to enable deep code analysis features.
        ignored_file_patterns (List[str]): Glob patterns for files to ignore during analysis.
        production_env_mapping (List[str]): Environment names considered as production.
    """
    enable_deep_analysis: bool = False
    ignored_file_patterns: List[str] = ['*.lock', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', '*.min.js', '*.min.css', '*.map', 'node_modules/*', 'dist/*', 'build/*', 'vendor/*', '*.svg', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.ico', '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx', '*.ppt', '*.pptx', '*.zip', '*.tar', '*.gz', '*.rar', '*.7z', '*.exe', '*.dll', '*.so', '*.dylib']
    production_env_mapping: List[str] = ['prod', 'production', 'prd', 'main']
    incident_label_patterns: List[str] = ['incident', 'production-error', 'P0', 'P1']
    change_failure_label_patterns: List[str] = ['change-failure', 'rollback']

    @field_validator('ignored_file_patterns', 'production_env_mapping', 'incident_label_patterns', 'change_failure_label_patterns', mode='before')
    @classmethod
    def split_str(cls, v):
        """Splits comma-separated strings into lists.

        Args:
            v (Union[str, List[str]]): The input value.

        Returns:
            List[str]: The list of strings.
        """
        if isinstance(v, str):
            return [i.strip() for i in v.split(',') if i.strip()]
        return v

class RateLimitSettings(BaseSettings):
    """Rate limiting configuration.

    Attributes:
        requests_per_second (int): Maximum number of requests allowed per second.
    """
    requests_per_second: int = 10

class ClientSettings(BaseSettings):
    """HTTP client configuration.

    Attributes:
        timeout (int): Request timeout in seconds.
        per_page (int): Number of items per page for paginated requests.
        max_retries (int): Maximum number of retries for failed requests.
    """
    timeout: int = 10
    per_page: int = 100
    max_retries: int = 5

class SchedulerSettings(BaseSettings):
    """Task scheduler configuration.

    Attributes:
        sync_interval_minutes (int): Interval in minutes between synchronization tasks.
    """
    sync_interval_minutes: int = 10

class LoggingSettings(BaseSettings):
    """Logging configuration.

    Attributes:
        level (str): The logging level (e.g., INFO, DEBUG).
    """
    level: str = 'INFO'

class SonarQubeSettings(BaseSettings):
    """SonarQube integration settings.

    Attributes:
        url (str): The SonarQube server URL.
        token (str): The authentication token.
        sync_interval_hours (int): Interval in hours between synchronization tasks.
        sync_issues (bool): Whether to synchronize issues.
    """
    url: str = ''
    token: str = ''
    sync_interval_hours: int = 24
    sync_issues: bool = False

class JenkinsSettings(BaseSettings):
    """Jenkins integration settings.

    Attributes:
        url (str): The Jenkins server URL.
        user (str): The username for authentication.
        token (str): The authentication token or API key.
        sync_interval_hours (int): Interval in hours between synchronization tasks.
        build_sync_limit (int): Maximum number of builds to sync per job.
    """
    url: str = ''
    user: str = ''
    token: str = ''
    sync_interval_hours: int = 12
    build_sync_limit: int = 100

class AISettings(BaseSettings):
    """AI service configuration.

    Attributes:
        api_key (str): The API key for the LLM service.
        base_url (str): The base URL of the LLM API.
        model (str): The name of the model to use.
    """
    api_key: str = ''
    base_url: str = 'https://api.openai.com/v1'
    model: str = 'gpt-4o'

class SLASettings(BaseSettings):
    """SLA threshold settings (in hours).
    
    Attributes:
        p0 (int): SLA response threshold for P0.
        p1 (int): SLA response threshold for P1.
        p2 (int): SLA response threshold for P2.
        p3 (int): SLA response threshold for P3.
        p4 (int): SLA response threshold for P4.
        default (int): Default SLA response threshold.
    """
    p0: int = 8
    p1: int = 24
    p2: int = 73
    p3: int = 120
    p4: int = 240
    default: int = 48

class StorageSettings(BaseSettings):
    """Local storage configuration.

    Attributes:
        data_dir (str): The directory path for persistent data storage.
    """
    data_dir: str = './data'

    @field_validator('data_dir')
    @classmethod
    def make_absolute(cls, v):
        """Ensures the data directory path is absolute.

        Args:
            v (str): The input path.

        Returns:
            str: The absolute path.
        """
        if not os.path.isabs(v):
            return os.path.join(os.getcwd(), v)
        return v

class Settings(BaseSettings):
    """Global application configuration model.

    Aggregates all specific setting sections into a single configuration object.

    Attributes:
        gitlab (GitLabSettings): GitLab settings.
        database (DatabaseSettings): Database settings.
        rabbitmq (RabbitMQSettings): RabbitMQ settings.
        analysis (AnalysisSettings): Analysis settings.
        ratelimit (RateLimitSettings): Rate limiting settings.
        client (ClientSettings): HTTP client settings.
        scheduler (SchedulerSettings): Scheduler settings.
        logging (LoggingSettings): Logging settings.
        sonarqube (SonarQubeSettings): SonarQube settings.
        jenkins (JenkinsSettings): Jenkins settings.
        ai (AISettings): AI settings.
        storage (StorageSettings): Storage settings.
    """
    gitlab: GitLabSettings = GitLabSettings()
    database: DatabaseSettings = DatabaseSettings()
    rabbitmq: RabbitMQSettings = RabbitMQSettings()
    analysis: AnalysisSettings = AnalysisSettings()
    ratelimit: RateLimitSettings = RateLimitSettings()
    client: ClientSettings = ClientSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    logging: LoggingSettings = LoggingSettings()
    sonarqube: SonarQubeSettings = SonarQubeSettings()
    jenkins: JenkinsSettings = JenkinsSettings()
    ai: AISettings = AISettings()
    storage: StorageSettings = StorageSettings()
    sla: SLASettings = SLASettings()
    model_config = SettingsConfigDict(env_file='.env', env_nested_delimiter='__', extra='ignore')

    @classmethod
    def load_from_ini(cls, path: str):
        """Loads configuration from a legacy config.ini file.

        Compatible with the `configparser` format.

        Args:
            path (str): The absolute path to the config.ini file.

        Returns:
            Settings: A populated Settings instance.
        """
        cp = configparser.ConfigParser()
        cp.read(path, encoding='utf-8')
        data = {}
        for section in cp.sections():
            data[section] = dict(cp.items(section))
        return cls.model_validate(data)
try:
    if os.path.exists(CONFIG_FILE_PATH):
        settings = Settings.load_from_ini(CONFIG_FILE_PATH)
    else:
        settings = Settings()
except Exception as e:
    print(f'⚠️ Warning: Failed to load config.ini, using defaults. Error: {e}')
    settings = Settings()

class Config:
    """向下兼容层，映射旧的全局变量名。
    
    建议新代码直接使用：from devops_collector.config import settings
    """
    GITLAB_URL = settings.gitlab.url
    GITLAB_TOKEN = settings.gitlab.private_token
    GITLAB_CLIENT_ID = settings.gitlab.client_id
    GITLAB_CLIENT_SECRET = settings.gitlab.client_secret
    GITLAB_REDIRECT_URI = settings.gitlab.redirect_uri
    DB_URI = settings.database.uri
    RAW_DATA_RETENTION_DAYS = settings.database.raw_data_retention_days
    RABBITMQ_HOST = settings.rabbitmq.host
    RABBITMQ_QUEUE = settings.rabbitmq.queue
    RABBITMQ_URL = settings.rabbitmq.url
    ENABLE_DEEP_ANALYSIS = settings.analysis.enable_deep_analysis
    IGNORED_FILE_PATTERNS = settings.analysis.ignored_file_patterns
    PRODUCTION_ENV_MAPPING = settings.analysis.production_env_mapping
    REQUESTS_PER_SECOND = settings.ratelimit.requests_per_second
    CLIENT_TIMEOUT = settings.client.timeout
    CLIENT_PER_PAGE = settings.client.per_page
    CLIENT_MAX_RETRIES = settings.client.max_retries
    SYNC_INTERVAL_MINUTES = settings.scheduler.sync_interval_minutes
    LOG_LEVEL = settings.logging.level
    SONARQUBE_URL = settings.sonarqube.url
    SONARQUBE_TOKEN = settings.sonarqube.token
    SONARQUBE_SYNC_INTERVAL_HOURS = settings.sonarqube.sync_interval_hours
    SONARQUBE_SYNC_ISSUES = settings.sonarqube.sync_issues
    JENKINS_URL = settings.jenkins.url
    JENKINS_USER = settings.jenkins.user
    JENKINS_TOKEN = settings.jenkins.token
    JENKINS_SYNC_INTERVAL_HOURS = settings.jenkins.sync_interval_hours
    JENKINS_BUILD_SYNC_LIMIT = settings.jenkins.build_sync_limit
    AI_API_KEY = settings.ai.api_key
    AI_BASE_URL = settings.ai.base_url
    AI_MODEL = settings.ai.model
    DATA_DIR = settings.storage.data_dir
    SLA_P0 = settings.sla.p0
    SLA_P1 = settings.sla.p1
    SLA_P2 = settings.sla.p2
    SLA_P3 = settings.sla.p3
    SLA_P4 = settings.sla.p4
    SLA_DEFAULT = settings.sla.default