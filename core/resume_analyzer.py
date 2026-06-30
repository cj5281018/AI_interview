"""
简历结构化分析模块 — 完整复刻参考项目

利用 LLM 对简历原文进行：
1. 结构化分段：将 OCR 文本拆分为 sections（个人信息/教育/项目/技能等）
2. 优化建议生成：识别 6 类常见问题并给出重写建议
3. Builder 数据提取：提取简历编辑器可用的结构化数据 + 自动检测模板

设计特点：
- 不依赖 LangChain，直接调用 OpenAI 兼容客户端
- 同步模式：analyze() 三步顺序执行
- 流式模式：analyze_stream() 第一步串行 + 二三步并行（threading）
- 多层 JSON 容错解析
"""
import json
import re
import uuid
import threading
import queue
from typing import Optional, Generator
from core.llm_client import OpenAICompatibleClient
from core.prompts.resume_parser_prompt import generate_parser_prompt


class ResumeAnalyzer:
    """简历结构化分析与优化建议生成器"""

    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat"):
        self.client = OpenAICompatibleClient(model=model, api_key=api_key, base_url=base_url)

    # ═══════════════════════════════
    # 同步分析入口
    # ═══════════════════════════════

    def analyze(self, ocr_text: str, job_title: str = "", report_context: Optional[dict] = None) -> dict:
        """同步分析：返回 {sections, suggestions, builder_data}"""
        sections = self._extract_sections(ocr_text)
        suggestions = self._generate_suggestions(sections, job_title, report_context=report_context)
        builder_data = self._extract_builder_data(ocr_text)
        return {"sections": sections, "suggestions": suggestions, "builder_data": builder_data}

    # ═══════════════════════════════
    # 流式分析入口：三步流水线，二三步并行
    # ═══════════════════════════════

    def analyze_stream(self, ocr_text: str, job_title: str = "", report_context: Optional[dict] = None) -> Generator[dict, None, None]:
        use_reasoning = hasattr(self.client, 'generate_stream_with_reasoning')

        def _collect_llm(messages) -> str:
            raw = ""
            if use_reasoning:
                for chunk_type, chunk in self.client.generate_stream_with_reasoning(messages):
                    if chunk_type == "content":
                        raw += chunk
            else:
                for chunk in self.client.generate_stream(messages):
                    raw += chunk
            return raw

        def _stream_llm(messages):
            if use_reasoning:
                for chunk_type, chunk in self.client.generate_stream_with_reasoning(messages):
                    if chunk_type == "thinking":
                        yield ("thinking", chunk)
                    else:
                        yield ("content", chunk)
            else:
                for chunk in self.client.generate_stream(messages):
                    yield ("thinking", chunk)

        # 第一步：结构化提取（串行）
        yield {"type": "stage", "stage": "正在解析简历结构..."}
        sections_raw = ""
        for kind, chunk in _stream_llm(self._build_sections_messages(ocr_text)):
            if kind == "thinking":
                yield {"type": "thinking", "chunk": chunk}
            else:
                sections_raw += chunk
        sections = self._parse_json_array(sections_raw, fallback_id_prefix="sec")

        # 第二步 & 第三步：并行执行
        yield {"type": "stage", "stage": "正在生成优化建议 & 提取结构化数据（并行）..."}
        thinking_q: queue.Queue = queue.Queue()
        suggestions_result = {"raw": "", "done": False}
        builder_result = {"raw": "", "done": False}

        def _run_suggestions():
            try:
                msgs = self._build_suggestions_messages(sections, job_title, report_context=report_context)
                if msgs:
                    suggestions_result["raw"] = _collect_llm(msgs)
            except Exception as e:
                print(f"[ResumeAnalyzer] suggestions thread error: {e}")
            suggestions_result["done"] = True
            thinking_q.put(None)

        def _run_builder():
            try:
                msgs = self._build_builder_messages(ocr_text)
                builder_result["raw"] = _collect_llm(msgs)
            except Exception as e:
                print(f"[ResumeAnalyzer] builder thread error: {e}")
            builder_result["done"] = True
            thinking_q.put(None)

        t1 = threading.Thread(target=_run_suggestions, daemon=True)
        t2 = threading.Thread(target=_run_builder, daemon=True)
        t1.start()
        t2.start()

        while not (suggestions_result["done"] and builder_result["done"]):
            try:
                thinking_q.get(timeout=0.5)
            except queue.Empty:
                yield {"type": "thinking", "chunk": "."}

        t1.join(timeout=5)
        t2.join(timeout=5)

        suggestions = self._parse_json_array(suggestions_result["raw"], fallback_id_prefix="sug") if suggestions_result["raw"] else []
        builder_data = self._parse_json_object(builder_result["raw"]) if builder_result["raw"] else {}
        builder_data = self._validate_builder_data(builder_data)

        yield {"type": "done", "result": {
            "sections": sections, "suggestions": suggestions, "builder_data": builder_data,
        }}

    # ═══════════════════════════════
    # 提示词构建
    # ═══════════════════════════════

    def _build_sections_messages(self, ocr_text: str) -> list:
        prompt = f"""你是一个专业的简历解析与排版专家。请将以下 OCR 识别的简历原文拆分为结构化 JSON 数组，并对每个段落的内容进行 Markdown 格式规整。

## 输出格式
每个 section 是一个 JSON 对象：
- "id": 唯一标识，格式 "sec_1", "sec_2" 等
- "type": 只能是：personal_info / education / projects / experience / skills / certifications / other
- "title": 段落标题（如"教育背景"、"项目经历"）
- "content": 规整后的 Markdown 文本

## Markdown 格式规整规则
1. 统一列表符号为 `- `，禁止出现 `·`、`•`、`*`
2. 有序列表使用标准编号，修复重复编号
3. 段落之间最多保留一个空行，列表项之间不要空行
4. 项目/经历用 `### 项目名称` 三级标题，紧接时间+标签，然后用列表写详情
5. 个人信息联系方式用 ` | ` 分隔
6. 保留 LaTeX 公式和 URL
7. 忠实原文，只做格式规整

请严格输出 JSON 数组，不要输出任何其他内容，不要用 markdown 代码块包裹。

简历原文：
{ocr_text[:5000]}"""
        return [
            {"role": "system", "content": "你是简历解析与排版专家。严格输出合法 JSON 数组。"},
            {"role": "user", "content": prompt},
        ]

    def _build_suggestions_messages(self, sections: list, job_title: str = "", report_context: Optional[dict] = None) -> list:
        analyzable = [s for s in sections if s.get("type") in ("experience", "projects", "skills", "education")]
        if not analyzable:
            return []
        job_context = f"目标岗位：{job_title}。" if job_title else ""
        sections_text = json.dumps(analyzable, ensure_ascii=False, indent=2)

        prompt = f"""{job_context}你是一位资深的硅谷大厂 HR 和简历优化专家。

请审查以下简历各段落，找出存在的问题并给出具体的重写建议。

常见问题类型：
- LACK_OF_METRICS: 缺乏量化指标
- WEAK_ACTION_VERB: 动词力度不足
- VAGUE_DESCRIPTION: 描述模糊
- MISSING_STAR: 不符合 STAR 法则
- ATS_KEYWORD_GAP: 缺少 ATS 关键词
- FORMAT_ISSUE: 格式问题

对每个发现的问题，输出一个 JSON 对象：
- "suggestionId": "sug_001" 格式
- "targetBlockId": 对应 section 的 id
- "targetField": "content"
- "issueType": 上述问题类型之一
- "issueLabel": 中文简短标签
- "originalText": 原始文本片段
- "suggestedText": 优化后的文本
- "reason": 修改理由
- "status": "PENDING"

请严格输出 JSON 数组，不要输出任何其他内容。

简历段落：
{sections_text}"""
        return [
            {"role": "system", "content": "你是简历优化专家，只输出合法 JSON 数组。"},
            {"role": "user", "content": prompt},
        ]

    def _build_builder_messages(self, ocr_text: str) -> list:
        system_prompt, user_prompt = generate_parser_prompt(ocr_text[:5000])
        template_instruction = """
另外，请根据简历内容判断最适合的模板风格，在 JSON 顶层增加 "detectedTemplate" 字段：
- "classic": 传统单栏  - "modern": 双栏布局  - "minimal": 极简纯文字
- "fresh": 应届生    - "tech": 技术岗位    - "creative": 创意岗位
- "executive": 商务  - "elegant": 管理层"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt + template_instruction},
        ]

    # ═══════════════════════════════
    # 各步骤独立调用
    # ═══════════════════════════════

    def _extract_sections(self, ocr_text: str) -> list:
        messages = self._build_sections_messages(ocr_text)
        raw = self.client.generate(messages)
        return self._parse_json_array(raw, fallback_id_prefix="sec")

    def _generate_suggestions(self, sections: list, job_title: str = "", report_context: Optional[dict] = None) -> list:
        messages = self._build_suggestions_messages(sections, job_title, report_context=report_context)
        if not messages:
            return []
        raw = self.client.generate(messages)
        return self._parse_json_array(raw, fallback_id_prefix="sug")

    def _extract_builder_data(self, ocr_text: str) -> dict:
        messages = self._build_builder_messages(ocr_text)
        raw = self.client.generate(messages)
        data = self._parse_json_object(raw)
        return self._validate_builder_data(data)

    # ═══════════════════════════════
    # JSON 容错解析（3 层降级）
    # ═══════════════════════════════

    @staticmethod
    def _parse_json_object(raw: str) -> dict:
        if not raw:
            return {}
        # 1) 直接解析
        try:
            result = json.loads(raw.strip())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
        # 2) 提取 markdown 代码块
        match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', raw)
        if match:
            try:
                result = json.loads(match.group(1))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        # 3) 第一个 { 到最后一个 }
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                result = json.loads(raw[start:end + 1])
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        return {}

    @staticmethod
    def _parse_json_array(raw: str, fallback_id_prefix: str = "item") -> list:
        if not raw:
            return []
        try:
            result = json.loads(raw.strip())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
        match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', raw)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        start = raw.find('[')
        end = raw.rfind(']')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
        return []

    @staticmethod
    def _validate_builder_data(data: dict) -> dict:
        valid_templates = {'classic', 'modern', 'minimal', 'fresh', 'tech', 'creative', 'executive', 'elegant'}
        if data.get('detectedTemplate') not in valid_templates:
            data['detectedTemplate'] = 'classic'
        if 'basicInfo' not in data:
            data['basicInfo'] = {}
        for key, default in {
            'name': '', 'gender': '', 'birthday': '', 'email': '',
            'mobile': '', 'location': '', 'workYears': '', 'photoUrl': '',
        }.items():
            if key not in data['basicInfo']:
                data['basicInfo'][key] = default
        if 'modules' not in data or not isinstance(data['modules'], list):
            data['modules'] = []
        for idx, module in enumerate(data['modules']):
            if 'id' not in module:
                module['id'] = f"mod_{uuid.uuid4().hex[:12]}"
            if 'visible' not in module:
                module['visible'] = True
            if 'sortIndex' not in module:
                module['sortIndex'] = idx
            if 'entries' in module and isinstance(module['entries'], list):
                for entry in module['entries']:
                    if 'id' not in entry:
                        entry['id'] = f"ent_{uuid.uuid4().hex[:12]}"
        return data
