from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class Paper:
    source: str
    external_id: str
    title: str
    authors: List[str]
    abstract: str
    primary_category: Optional[str]
    categories: List[str]
    link: str
    published: Optional[datetime]
    updated: Optional[datetime]
    comment: Optional[str]
    direction: Optional[str]
    direction_scores: Dict[str, float]
    summary: Optional[str]
    method_improvement: Optional[str]
    experiments: Optional[str]
    venue_name: Optional[str]
    venue_year: Optional[str]
    venue_status: Optional[str]
    venue_ccf_level: Optional[str]
    match_confidence: Optional[float]

