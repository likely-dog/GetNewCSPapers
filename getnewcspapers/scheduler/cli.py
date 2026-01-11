import argparse
from typing import List
from pathlib import Path
from ..storage import db
from ..sources.arxiv_client import fetch_recent_by_query
from ..classify.rule_classifier import classify_direction
from ..summarize.llm_summarizer import summarize_with_deepseek
from ..venue.detector import detect_from_comment, map_ccf_level
from ..delivery.html_report import render_html


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--areas", type=str, required=True, help="以逗号分隔的兴趣方向，最多5个")
    ap.add_argument("--max", type=int, default=10)
    ap.add_argument("--out", type=str, default="daily_report.html")
    return ap.parse_args()


def build_arxiv_queries(directions: List[str]):
    queries = []
    for d in directions:
        if "人工智能" in d:
            queries.append('cat:cs.AI OR cat:cs.LG OR cat:stat.ML')
        elif "计算机网络" in d:
            queries.append('cat:cs.NI')
        elif "网络与信息安全" in d:
            queries.append('cat:cs.CR')
        elif "软件工程" in d or "程序设计语言" in d or "系统软件" in d:
            queries.append('cat:cs.SE OR cat:cs.PL OR cat:cs.OS')
        elif "数据库" in d or "数据挖掘" in d or "内容检索" in d:
            queries.append('cat:cs.DB OR cat:cs.IR')
        elif "计算机科学理论" in d:
            queries.append('cat:cs.CC OR cat:cs.DS OR cat:cs.LO')
        elif "图形学" in d or "多媒体" in d:
            queries.append('cat:cs.GR OR cat:cs.MM')
        elif "人机交互" in d or "普适计算" in d:
            queries.append('cat:cs.HC')
        elif "体系结构" in d or "并行与分布" in d or "存储系统" in d:
            queries.append('cat:cs.AR OR cat:cs.DC OR cat:cs.SY')
        else:
            queries.append('cat:cs.*')
    return queries


def run_once(directions: List[str], max_per_day: int, out_path: Path):
    db.init_db()
    db.save_preferences(directions, "08:00", max_per_day)
    queries = build_arxiv_queries(directions)
    collected = []
    for q in queries:
        for p in fetch_recent_by_query(q, max_results=80):
            d, scores = classify_direction(p.title, p.abstract, p.primary_category or "")
            p.direction = d
            p.direction_scores = scores
            summ = summarize_with_deepseek(p.title, p.abstract, p.direction)
            if summ:
                p.summary = summ.get("summary")
                p.method_improvement = summ.get("method_improvement")
                p.experiments = summ.get("experiments")
                if not p.direction and summ.get("direction"):
                    p.direction = summ.get("direction")
            venue_name, venue_year, venue_status = detect_from_comment(p.comment)
            p.venue_name = venue_name
            p.venue_year = venue_year
            p.venue_status = venue_status
            level, mapped_dir = map_ccf_level(venue_name)
            p.venue_ccf_level = level
            db.upsert_paper(p)
            if p.direction and p.direction in directions:
                collected.append(p)
    collected = collected[:max_per_day]
    rows = []
    for p in collected:
        rows.append({
            "source": p.source,
            "external_id": p.external_id,
            "title": p.title,
            "authors": p.authors,
            "abstract": p.abstract,
            "link": p.link,
            "direction": p.direction,
            "summary": p.summary,
            "method_improvement": p.method_improvement,
            "experiments": p.experiments,
            "venue_name": p.venue_name,
            "venue_year": p.venue_year,
            "venue_status": p.venue_status,
            "venue_ccf_level": p.venue_ccf_level,
        })
    render_html(rows, directions, out_path)
    db.mark_papers_pushed([p.external_id for p in collected])


def main():
    args = parse_args()
    directions = [s.strip() for s in args.areas.split(",") if s.strip()]
    directions = directions[:5]
    run_once(directions, args.max, Path(args.out))


if __name__ == "__main__":
    main()
