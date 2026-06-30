"""
职业规划服务（简化版）

基于面试评估结果生成职业发展建议和学习路线。
"""
import json
import re
from typing import Dict, List, Optional
from core.llm_client import OpenAICompatibleClient


class CareerPlanningService:
    """职业规划服务"""

    def __init__(self, llm_client: Optional[OpenAICompatibleClient] = None):
        self.llm_client = llm_client

    def generate_learning_plan(
        self,
        evaluations: List[Dict],
        weaknesses: str = "",
        target_role: str = "",
    ) -> Dict:
        """
        基于评估结果生成学习计划

        Args:
            evaluations: 评估列表 [{"dimension": str, "score": int, "comment": str}]
            weaknesses: 不足描述
            target_role: 目标岗位

        Returns:
            {
                "plan_title": str,
                "weekly_tasks": [{"week": int, "topic": str, "tasks": [str], "resources": [str]}],
                "total_weeks": int
            }
        """
        if not self.llm_client:
            return {"plan_title": "请先配置 LLM API Key", "weekly_tasks": [], "total_weeks": 0}

        # 构建评估摘要
        eval_summary = "\n".join(
            f"- {e['dimension']}: {e['score']}/10 - {e['comment']}"
            for e in evaluations
        )

        prompt = f"""你是一位资深的职业规划导师。根据以下面试评估结果，为候选人制定一份为期4-6周的学习提升计划。

面试评估结果：
{eval_summary}

不足之处：
{weaknesses or "参见评估结果"}

目标岗位：{target_role or "参见评估结果"}

请按以下 JSON 格式输出（不要输出其他内容）：
{{
  "plan_title": "学习计划标题",
  "weekly_tasks": [
    {{
      "week": 1,
      "topic": "本周主题",
      "tasks": ["具体任务1", "具体任务2"],
      "resources": ["推荐资源1", "推荐资源2"]
    }}
  ],
  "total_weeks": 4
}}"""

        messages = [
            {"role": "system", "content": "你是一位资深的职业规划导师，擅长制定技术学习路线。"},
            {"role": "user", "content": prompt},
        ]

        try:
            raw = self.llm_client.generate(messages)
            json_match = re.search(r"\{[\s\S]*\}", raw)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"[career] 生成学习计划失败: {e}")

        return {"plan_title": "生成失败", "weekly_tasks": [], "total_weeks": 0}

    def generate_career_advice(
        self,
        all_evaluations: List[Dict],
    ) -> str:
        """
        基于多次面试的历史评估生成综合职业建议

        Args:
            all_evaluations: 历次面试的评估汇总
                [{"session_id": str, "position": str, "date": str, "evaluations": [...]}]

        Returns:
            职业建议文本
        """
        if not self.llm_client:
            return "请先配置 LLM API Key"

        # 构建历史摘要
        history_lines = []
        for item in all_evaluations[-5:]:  # 最近5次
            avg = (
                sum(e["score"] for e in item.get("evaluations", []))
                / len(item["evaluations"])
                if item.get("evaluations")
                else 0
            )
            history_lines.append(
                f"- [{item.get('date', '')}] {item.get('position', '未知岗位')} "
                f"综合评分: {avg:.1f}/10"
            )

        prompt = f"""你是一位职业规划导师。以下是候选人历次模拟面试的评估汇总：

{chr(10).join(history_lines)}

请给出2-3条具体的职业发展建议，包括：技能提升方向、适合的岗位类型、面试准备策略。
用中文回复，每条建议100字以内，要具体可操作。"""

        messages = [
            {"role": "system", "content": "你是职业规划导师，给出具体、可操作的建议。"},
            {"role": "user", "content": prompt},
        ]

        try:
            return self.llm_client.generate(messages)
        except Exception as e:
            return f"生成建议失败: {e}"

    def build_radar_data(self, evaluations: List[Dict]) -> Dict:
        """
        将评估数据转换为雷达图数据格式

        Returns:
            {"dimensions": [str], "scores": [int], "max_score": 10}
        """
        if not evaluations:
            return {"dimensions": [], "scores": [], "max_score": 10}

        return {
            "dimensions": [e["dimension"] for e in evaluations],
            "scores": [e["score"] for e in evaluations],
            "max_score": 10,
        }
