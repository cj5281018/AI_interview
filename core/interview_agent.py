"""
面试 Agent 核心模块（简化版）

直接使用 OpenAI 兼容客户端调用 LLM，不依赖 LangChain。
保留原项目的核心功能：多模型支持、流式响应、思维链分离、面试评估。
"""
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Generator, Tuple
from core.llm_client import OpenAICompatibleClient


class InterviewAgent:
    """
    AI 面试官核心类

    负责管理面试对话流程，包括：
    - 多模型兼容（DeepSeek / 阿里云通义千问）
    - 对话记忆管理（滑动窗口）
    - 流式响应（思维链 + 正式回复分离）
    - 面试评估（多维度评分报告）
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_history_turns: int = 10,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model
        self.max_history_turns = max_history_turns
        self.temperature = temperature

        # LLM 客户端
        self.llm_client: Optional[OpenAICompatibleClient] = None
        if api_key and base_url:
            self.llm_client = OpenAICompatibleClient(
                model=model, api_key=api_key, base_url=base_url
            )

        # 对话历史
        self.chat_history: List[Dict[str, str]] = []

        # 加载提示词配置
        self.prompt_config = self._load_prompt_config()
        self.prompt = self._build_prompt()
        self.current_style = "default"

    # ══════════════════════════════════════════════
    # 提示词管理
    # ══════════════════════════════════════════════

    def _load_prompt_config(self) -> Dict:
        """加载提示词配置文件"""
        import os
        config_path = os.path.join(os.path.dirname(__file__), "prompts.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "interviewer": {
                    "system_prompt": "你是一位专业的 AI 面试官。",
                    "greeting": "你好，欢迎参加面试。",
                },
                "styles": {"default": {"name": "默认", "injection": ""}},
            }

    def _build_prompt(self) -> str:
        """构建系统提示词"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        role_config = self.prompt_config.get("interviewer", {})
        base = role_config.get("system_prompt", "你是一位 AI 面试官。")
        return f"[当前时间: {now}]\n\n{base}"

    def get_greeting(self) -> str:
        """获取面试开场白"""
        return self.prompt_config.get("interviewer", {}).get(
            "greeting", "你好，欢迎参加面试。"
        )

    def get_available_styles(self) -> List[Dict]:
        """获取所有可用的面试风格"""
        styles = self.prompt_config.get("styles", {})
        return [
            {"key": k, "name": v.get("name", k), "description": v.get("description", "")}
            for k, v in styles.items()
        ]

    def set_style(self, style_key: str):
        """切换面试风格"""
        self.current_style = style_key

    def _get_style_injection(self) -> str:
        """获取当前风格的提示词注入"""
        style = self.prompt_config.get("styles", {}).get(self.current_style, {})
        return style.get("injection", "")

    # ══════════════════════════════════════════════
    # 对话管理
    # ══════════════════════════════════════════════

    def _build_messages(
        self, user_input: str, context: str = ""
    ) -> List[Dict[str, str]]:
        """
        构建发给 LLM 的完整消息列表

        结构: [system_prompt] + [style_injection] + [context] + [chat_history] + [user_input]
        """
        messages = [{"role": "system", "content": self.prompt}]

        # 注入风格提示词
        style_injection = self._get_style_injection()
        if style_injection:
            messages.append({"role": "system", "content": style_injection})

        # 注入上下文（简历信息等）
        if context:
            messages.append({
                "role": "system",
                "content": f"以下是候选人的简历信息，请基于此进行面试提问:\n\n{context}",
            })

        # 添加历史对话
        messages.extend(self.chat_history)

        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

    def _add_to_history(self, role: str, content: str):
        """添加消息到对话历史，自动控制长度"""
        self.chat_history.append({"role": role, "content": content})
        if self.max_history_turns > 0:
            max_msgs = self.max_history_turns * 2
            if len(self.chat_history) > max_msgs:
                self.chat_history = self.chat_history[-max_msgs:]

    def reset_memory(self):
        """清空对话记忆"""
        self.chat_history.clear()

    def get_chat_history(self) -> List[Dict]:
        """获取当前对话历史"""
        return list(self.chat_history)

    # ══════════════════════════════════════════════
    # 对话执行
    # ══════════════════════════════════════════════

    def run(self, user_input: str, context: str = "") -> str:
        """
        执行一次完整的对话调用（同步模式）

        Args:
            user_input: 用户输入
            context: 附加上下文（如简历摘要等）

        Returns:
            AI 面试官的回复
        """
        if not self.llm_client:
            return "⚠️ LLM 客户端未初始化，请先配置 API Key。"

        messages = self._build_messages(user_input, context)
        response = self.llm_client.generate(messages)

        self._add_to_history("user", user_input)
        self._add_to_history("assistant", response)

        return response

    def run_stream(
        self, user_input: str, context: str = ""
    ) -> Generator[Tuple[str, str], None, None]:
        """
        流式对话调用，逐 chunk 返回

        Yields:
            ("thinking", chunk) — 思维链
            ("content", chunk)  — 正式回复
        """
        if not self.llm_client:
            yield ("content", "⚠️ LLM 客户端未初始化，请先配置 API Key。")
            return

        messages = self._build_messages(user_input, context)
        full_response = ""

        try:
            for chunk_type, chunk in self.llm_client.generate_stream_with_reasoning(messages):
                if chunk_type == "content":
                    full_response += chunk
                yield (chunk_type, chunk)
        except Exception as e:
            yield ("content", f"\n[错误: {e}]")

        self._add_to_history("user", user_input)
        self._add_to_history("assistant", full_response)

    # ══════════════════════════════════════════════
    # 面试评估
    # ══════════════════════════════════════════════

    def evaluate_interview(self) -> Dict:
        """
        基于完整对话历史生成面试评估报告

        Returns:
            {
                "evaluations": [{"dimension": str, "score": int, "comment": str}],
                "strengths": str,
                "weaknesses": str,
                "summary": str
            }
        """
        if not self.chat_history:
            return {}

        eval_prompt = """你是一位资深面试评估专家。请根据以下面试对话记录，生成一份客观、专业的面试评估报告。

请严格按照以下 JSON 格式输出（不要输出任何其他内容）：
{
  "evaluations": [
    {"dimension": "技术深度", "score": 1-10整数, "comment": "一句话点评"},
    {"dimension": "沟通表达", "score": 1-10整数, "comment": "一句话点评"},
    {"dimension": "逻辑思维", "score": 1-10整数, "comment": "一句话点评"},
    {"dimension": "项目经验", "score": 1-10整数, "comment": "一句话点评"},
    {"dimension": "学习潜力", "score": 1-10整数, "comment": "一句话点评"}
  ],
  "strengths": "2-3句话总结候选人的优势亮点",
  "weaknesses": "2-3句话总结不足和改进建议",
  "summary": "1-2句话的总体评价"
}

评分标准：1-3分=明显不足，4-5分=基本合格，6-7分=良好，8-9分=优秀，10分=卓越"""

        # 构建对话摘要（限制每个消息长度）
        history_text = ""
        for msg in self.chat_history:
            role_label = "面试官" if msg["role"] == "assistant" else "候选人"
            content = msg["content"][:500]
            history_text += f"{role_label}: {content}\n\n"

        messages = [
            {"role": "system", "content": eval_prompt},
            {"role": "user", "content": f"对话记录：\n\n{history_text}\n\n请生成评估报告。"},
        ]

        try:
            if self.llm_client:
                raw = self.llm_client.generate(messages)
                json_match = re.search(r"\{[\s\S]*\}", raw)
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            print(f"[agent] 评估生成失败: {e}")

        return {}
