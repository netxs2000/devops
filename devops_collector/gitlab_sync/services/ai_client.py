# -*- coding: utf-8 -*-
"""AI 服务适配器模块。

提供与大语言模型 (LLM) 交互的统一接口。
"""

import logging
import httpx
import json
from typing import List, Dict, Any, Optional
from devops_collector.config import Config

logger = logging.getLogger(__name__)

class AIClient:
    """AI 客户端，封装 Prompt 工程与 LLM 通信。"""

    def __init__(self):
        self.api_key = Config.AI_API_KEY
        self.base_url = Config.AI_BASE_URL
        self.model = Config.AI_MODEL
        self.timeout = 30.0

    async def chat(self, prompt: str, system_msg: str = "你是一个专业的软件质量保证 (QA) 专家和资深测试工程师。") -> str:
        """调用大模型进行对话。

        Args:
            prompt (str): 用户输入。
            system_msg (str): 系统 Prompt。

        Returns:
            str: 模型返回的文本内容。
        """
        if not self.api_key:
            logger.warning("AI_API_KEY is not configured. Returning fallback simulated response.")
            return self._get_fallback_response(prompt)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return self._get_fallback_response(prompt)

    def _get_fallback_response(self, prompt: str) -> str:
        """如果 AI 未配置或失效，提供模拟回复。"""
        if "验收标准" in prompt:
            return json.dumps([
                {"action": "打开关联的功能页面并检查初始状态", "expected": "页面加载正常，无报错"},
                {"action": "按照验收标准执行核心业务路径输入", "expected": "系统响应符合预期逻辑，数据正确保存"},
                {"action": "验证边界值和负向测试场景", "expected": "系统能够正确处理异常并提供友好提示"}
            ], ensure_ascii=False)
        return "AI 功能暂时无法连接，请检查配置。"

    async def generate_steps_from_ac(self, requirement_title: str, ac_list: List[str]) -> List[Dict[str, str]]:
        """[核心功能] 将验收标准转化为结构化的测试步骤。

        Args:
            requirement_title (str): 需求标题。
            ac_list (List[str]): 验收标准列表。

        Returns:
            List[Dict[str, str]]: 包含 action 和 expected 的步骤列表。
        """
        if not ac_list:
            return []

        prompt = f"""
        请根据以下软件需求及其验收标准 (AC)，生成一套完整的、可执行的测试用例步骤。
        要求：
        1. 步骤必须具体，具有可操作性。
        2. 覆盖所有提供的验收标准。
        3. 必须以 JSON 数组格式返回，每个元素包含 "action" (操作步骤) 和 "expected" (预期结果) 两个字段。
        4. 不要包含任何解释性文本，只返回 JSON 数组。

        需求标题: {requirement_title}
        验收标准:
        {chr(10).join([f"- {ac}" for ac in ac_list])}
        """

        response_text = await self.chat(prompt)
        
        try:
            # 尝试清洗 Markdown 代码块
            clean_json = response_text.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif clean_json.startswith("```"):
                clean_json = clean_json.split("```")[1].split("```")[0].strip()
                
            steps = json.loads(clean_json)
            if isinstance(steps, list):
                return steps
            return []
        except Exception as e:
            logger.error(f"Failed to parse AI response JSON: {e}. Raw content: {response_text}")
            return []
