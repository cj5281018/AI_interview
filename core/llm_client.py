"""
LLM 客户端封装 — 兼容 OpenAI API 的所有模型提供商

支持 DeepSeek、阿里云通义千问等任何兼容 OpenAI 接口的服务。
提供同步调用和流式调用两种模式，流式模式支持思维链分离。
"""
from typing import Generator, Tuple
from openai import OpenAI


class OpenAICompatibleClient:
    """
    通用的 OpenAI 兼容接口 LLM 客户端

    用法:
        client = OpenAICompatibleClient(
            model="deepseek-chat",
            api_key="sk-xxx",
            base_url="https://api.deepseek.com/v1"
        )
        answer = client.generate([{"role": "user", "content": "你好"}])
    """

    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    # ── 同步调用 ──
    def generate(self, messages: list) -> str:
        """调用 LLM 生成完整回复"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[错误] 调用 LLM 失败: {e}"

    # ── 流式调用（仅返回内容）──
    def generate_stream(self, messages: list) -> Generator[str, None, None]:
        """流式调用 LLM，逐 chunk 返回文本"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            yield f"[错误: {e}]"

    # ── 流式调用（含思维链）──
    def generate_stream_with_reasoning(
        self, messages: list
    ) -> Generator[Tuple[str, str], None, None]:
        """
        流式调用，区分思维链和正式回复。

        yield ("thinking", chunk) — 思维链（仅部分模型支持）
        yield ("content", chunk)  — 正式回复
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    yield ("thinking", reasoning)
                if delta.content:
                    yield ("content", delta.content)
        except Exception as e:
            yield ("content", f"[错误: {e}]")
