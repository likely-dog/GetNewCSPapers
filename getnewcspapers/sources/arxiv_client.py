from typing import List
import arxiv
from dateutil import parser as dateparser
from ..models import Paper


def fetch_recent_by_query(query: str, max_results: int = 100) -> List[Paper]:
    client = arxiv.Client()
    search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.SubmittedDate)
    results = []
    for r in client.results(search):
        primary = getattr(r, "primary_category", None)
        cats = [t.term for t in getattr(r, "tags", [])] if getattr(r, "tags", None) else []
        published = r.published if r.published else None
        updated = r.updated if r.updated else None
        p = Paper(
            source="arxiv",
            external_id=r.get_short_id(),
            title=r.title,
            authors=[a.name for a in r.authors],
            abstract=r.summary,
            primary_category=primary,
            categories=cats,
            link=r.entry_id,
            published=published,
            updated=updated,
            comment=getattr(r, "comment", None),
            direction=None,
            direction_scores={},
            summary=None,
            method_improvement=None,
            experiments=None,
            venue_name=None,
            venue_year=None,
            venue_status=None,
            venue_ccf_level=None,
            match_confidence=None,
        )
        results.append(p)
    return results
