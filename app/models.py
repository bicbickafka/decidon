from pydantic import BaseModel
from typing import Optional

class LegislatureOut(BaseModel):
    legislature_id: str
    institution: str
    name: str
    start_date: str
    end_date: str
    wikidata_qid: Optional[str] = None
    wikipedia_url: Optional[str] = None

class MandateOut(BaseModel):
    legislature_id: str
    institution: str
    legislature_name: str
    position: Optional[str] = None
    group: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class PersonOut(BaseModel):
    person_id: str
    last_name: str
    first_name: Optional[str] = None
    birth_date: Optional[str] = None
    death_date: Optional[str] = None
    wikidata_qid: Optional[str] = None
    wikipedia_url: Optional[str] = None
    sycomore_id: Optional[str] = None
    senat_id: Optional[str] = None

class PersonDetailOut(PersonOut):
    mandates: list[MandateOut] = []