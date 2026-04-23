from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date # Import crucial

class LegislatureOut(BaseModel):
    legislature_id: str
    institution: str
    name: str
    start_date: date # Utilisation du type date
    end_date: date
    wikidata_qid: Optional[str] = None
    wikipedia_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class MandateOut(BaseModel):
    legislature_id: str
    institution: str
    legislature_name: str
    position: Optional[str] = None
    group: Optional[str] = None
    start_date: Optional[date] = None # Utilisation de Optional[date]
    end_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)

class PersonOut(BaseModel):
    person_id: str
    last_name: str
    first_name: Optional[str] = None
    birth_date: Optional[date] = None # Utilisation de Optional[date]
    death_date: Optional[date] = None
    wikidata_qid: Optional[str] = None
    wikipedia_url: Optional[str] = None
    sycomore_id: Optional[str] = None
    senat_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class PersonDetailOut(PersonOut):
    mandates: list[MandateOut] = []