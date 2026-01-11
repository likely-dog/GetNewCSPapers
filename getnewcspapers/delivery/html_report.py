from pathlib import Path
from typing import List
from jinja2 import Template

TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>每日预印本推送</title>
<style>
body { font-family: system-ui, sans-serif; padding: 20px; }
.paper { margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px solid #ddd; }
.title { font-weight: 600; font-size: 16px; }
.meta { color: #666; font-size: 12px; }
.section { margin-top: 6px; }
</style>
</head>
<body>
<h2>每日预印本推送</h2>
<div>方向：{{ direction_list }}</div>
<div>篇目：{{ papers|length }}</div>
{% for p in papers %}
<div class="paper">
  <div class="title"><a href="{{ p['link'] }}" target="_blank">{{ p['title'] }}</a></div>
  <div class="meta">{{ ', '.join(p['authors']) }} | {{ p['source'] }} | {{ p['external_id'] }} | {{ p.get('direction','') }}</div>
  <div class="section">摘要：{{ p.get('summary') or p.get('abstract') }}</div>
  {% if p.get('method_improvement') %}<div class="section">方法/改进：{{ p['method_improvement'] }}</div>{% endif %}
  {% if p.get('experiments') %}<div class="section">实验：{{ p['experiments'] }}</div>{% endif %}
  {% if p.get('venue_name') %}<div class="section">会议信息：{{ p['venue_name'] }} {{ p.get('venue_year') or '' }}（{{ p.get('venue_status') or '' }}，CCF {{ p.get('venue_ccf_level') or '未知' }}）</div>{% endif %}
</div>
{% endfor %}
</body>
</html>
"""


def render_html(papers: List[dict], directions: List[str], out_path: Path):
    tpl = Template(TEMPLATE)
    html = tpl.render(papers=papers, direction_list="、".join(directions))
    out_path.write_text(html, encoding="utf-8")

def render_html_string(papers: List[dict], directions: List[str]) -> str:
    tpl = Template(TEMPLATE)
    return tpl.render(papers=papers, direction_list="、".join(directions))
