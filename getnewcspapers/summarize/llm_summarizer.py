import os
from typing import Optional, Dict

def build_prompt(title: str, abstract: str, direction_hint: Optional[str]) -> str:
    return (
        "请基于题目与摘要，输出JSON，字段：direction, summary, method_improvement, experiments, venue_hint。\n"
        f"题目：{title}\n"
        f"摘要：{abstract}\n"
        f"方向提示：{direction_hint or ''}\n"
        "仅输出JSON，不要额外文本。"
    )


def summarize_with_deepseek(title: str, abstract: str, direction_hint: Optional[str]) -> Optional[Dict[str, str]]:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是严谨的学术助手，按要求输出JSON"},
                {"role": "user", "content": build_prompt(title, abstract, direction_hint)},
            ],
        )
        content = resp.choices[0].message.content
        import json
        return json.loads(content)
    except Exception:
        return None
