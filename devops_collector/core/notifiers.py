"""多渠道通知服务 (Multi-channel Notifier)

负责将 DevOps 效能平台的风险告警通过 Webhook 推送到企业微信、飞书、钉钉。
"""
import requests
import logging
import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
logger = logging.getLogger(__name__)

class BaseBot(ABC):
    """通知机器人基类。"""

    def __init__(self, webhook_url: str):
        '''"""TODO: Add description.

Args:
    self: TODO
    webhook_url: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.webhook_url = webhook_url

    @abstractmethod
    def send_risk_card(self, title: str, details: List[Dict[str, str]], level: str='HIGH') -> bool:
        """发送结构化的风险预警卡片。"""
        pass

class WeComBot(BaseBot):
    """企业微信机器人 Webhook 客户端。"""

    def send_risk_card(self, title: str, details: List[Dict[str, str]], level: str='HIGH') -> bool:
        '''"""TODO: Add description.

Args:
    self: TODO
    title: TODO
    details: TODO
    level: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        color = 'warning' if level == 'HIGH' else 'info'
        markdown_lines = [f'### <font color="{color}">{title}</font>', '---']
        for detail in details:
            for k, v in detail.items():
                markdown_lines.append(f'> **{k}**: {v}')
        markdown_lines.append('\n---\n*请相关负责人尽快处理，点击查看 [DevInsight 控制台](https://devops.corp.com)*')
        data = {'msgtype': 'markdown', 'markdown': {'content': '\n'.join(markdown_lines)}}
        return self._post(data)

    def _post(self, data: dict) -> bool:
        '''"""TODO: Add description.

Args:
    self: TODO
    data: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        try:
            res = requests.post(self.webhook_url, json=data, timeout=10)
            return res.json().get('errcode') == 0
        except Exception as e:
            logger.error(f'WeCom post error: {e}')
            return False

class FeishuBot(BaseBot):
    """飞书机器人 Webhook 客户端。"""

    def send_risk_card(self, title: str, details: List[Dict[str, str]], level: str='HIGH') -> bool:
        '''"""TODO: Add description.

Args:
    self: TODO
    title: TODO
    details: TODO
    level: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        config_map = {'HIGH': 'red', 'MEDIUM': 'orange', 'LOW': 'blue'}
        template = config_map.get(level, 'grey')
        md_content = ''
        for detail in details:
            for k, v in detail.items():
                md_content += f'**{k}**: {v}\\n'
        data = {'msg_type': 'interactive', 'card': {'header': {'template': template, 'title': {'tag': 'plain_text', 'content': title}}, 'elements': [{'tag': 'div', 'text': {'tag': 'lark_md', 'content': md_content}}, {'tag': 'hr'}, {'tag': 'note', 'elements': [{'tag': 'plain_text', 'content': 'DevOps 效能平台自动推送'}]}]}}
        try:
            res = requests.post(self.webhook_url, json=data, timeout=10)
            return res.json().get('code') == 0 or res.json().get('StatusCode') == 0
        except Exception as e:
            logger.error(f'Feishu post error: {e}')
            return False

class DingTalkBot(BaseBot):
    """钉钉机器人 Webhook 客户端。"""

    def send_risk_card(self, title: str, details: List[Dict[str, str]], level: str='HIGH') -> bool:
        '''"""TODO: Add description.

Args:
    self: TODO
    title: TODO
    details: TODO
    level: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        md_text = f'### {title}\n\n---\n\n'
        for detail in details:
            for k, v in detail.items():
                md_text += f'- **{k}**: {v}\n'
        data = {'msgtype': 'markdown', 'markdown': {'title': title, 'text': md_text}}
        try:
            res = requests.post(self.webhook_url, json=data, timeout=10)
            return res.json().get('errcode') == 0
        except Exception as e:
            logger.error(f'DingTalk post error: {e}')
            return False