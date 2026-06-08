"""
schemas.py
Pydantic schemas — API serialization layer.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import date
from app.models import InstitutionType


class LegislatureOut(BaseModel):
    legislature_id: str
    institution: InstitutionType
    name: str
    start_date: date
    end_date: date
    wikidata_qid: Optional[str] = None
    wikipedia_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MandateOut(BaseModel):
    legislature_id: str
    institution: str
    legislature_name: str
    position: Optional[str] = None
    role: Optional[str] = None
    constituency: Optional[str] = None
    group: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class PersonOut(BaseModel):
    person_id: str
    last_name: str
    first_name: str
    alias: Optional[str] = None
    birth_date: Optional[date] = None
    death_date: Optional[date] = None
    wikidata_qid: Optional[str] = None
    wikipedia_url: Optional[str] = None
    sycomore_id: Optional[str] = None
    senat_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PersonDetailOut(PersonOut):
    mandates: list[MandateOut] = []


class PersonMandateGroupOut(BaseModel):
    person: PersonOut
    mandates: list[MandateOut]

    model_config = ConfigDict(from_attributes=True)


class PersonMandateGroupSearchResponse(BaseModel):
    total_groups: int
    limit: int
    offset: int
    items: list[PersonMandateGroupOut]


class MandateRowOut(BaseModel):
    mandate_id: int
    person_id: str
    last_name: str
    first_name: str
    alias: Optional[str] = None
    position: Optional[str] = None
    constituency: Optional[str] = None
    legislature_id: str
    legislature_name: str
    institution: str
    group: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class MandateSearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[MandateRowOut]


class ParsedMentionOut(BaseModel):
    raw: str
    normalized_raw: str
    scenario: int
    first_name_or_initial: Optional[str] = None
    last_name: Optional[str] = None
    constituency: Optional[str] = None
    title: Optional[str] = None
    role: Optional[str] = None
    alias: Optional[str] = None


class MatchScoreComponentsOut(BaseModel):
    whoosh_score: float
    date_match: bool
    name_similarity: float
    surname_match: bool
    alias_match: bool
    constituency_match: bool
    role_match: bool
    title_match: bool
    initial_match: bool


class MatchCandidateOut(BaseModel):
    person_id: str
    match_score: float
    institution: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    alias: Optional[str] = None
    mandate_id: Optional[str] = None
    legislature_id: Optional[str] = None
    legislature_name: Optional[str] = None
    position: Optional[str] = None
    role: Optional[str] = None
    constituency: Optional[str] = None
    active_from: Optional[date] = None
    active_until: Optional[date] = None
    score_components: MatchScoreComponentsOut


class MatchResponse(BaseModel):
    query: str
    session_date: Optional[date] = None
    scenario: int
    parsed: ParsedMentionOut
    total_candidates: int
    items: list[MatchCandidateOut]
    note: Optional[str] = None