import pandas as pd
from sqlalchemy import create_engine, Column, String, text
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite:////home/mfresq/PycharmProjects/decidon/app/data/prosopography.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

class Base(DeclarativeBase):
    pass

class Person(Base):
    __tablename__ = "persons"
    person_id       = Column(String, primary_key=True)
    last_name       = Column(String, index=True)
    first_name      = Column(String)
    alias           = Column(String)
    birth_date      = Column(String)
    death_date      = Column(String)
    wikidata_qid    = Column(String)
    wikipedia_url   = Column(String)
    sycomore_id     = Column(String)
    senat_id        = Column(String)

class Legislature(Base):
    __tablename__ = "legislatures"
    legislature_id  = Column(String, primary_key=True)
    institution     = Column(String, index=True)
    name            = Column(String)
    start_date      = Column(String)
    end_date        = Column(String)
    wikidata_qid    = Column(String)
    wikipedia_url   = Column(String)

class Mandate(Base):
    __tablename__ = "mandates"
    id              = Column(String, primary_key=True)
    person_id       = Column(String, index=True)
    legislature_id  = Column(String, index=True)
    position        = Column(String)
    group           = Column(String, index=True)
    start_date      = Column(String)
    end_date        = Column(String)

def load_data(tsv_path: str = "/home/mfresq/PycharmProjects/decidon/app/data/prosopography.tsv"):
    """Load TSV into SQLite. Safe to run multiple times."""
    Base.metadata.create_all(engine)
    df = pd.read_csv(tsv_path, sep="\t", dtype=str).fillna("")

    # Traitement des personnes
    persons = df[[
        "person_id", "person_last_name", "person_first_name", "person_alias",
        "person_birth_date", "person_death_date", "person_wikidata_qid",
        "person_wikipedia_url", "person_sycomore_id", "person_senat_id"
    ]].drop_duplicates("person_id")
    persons = persons.rename(columns={c: c.replace("person_", "") for c in persons.columns if c != "person_id"})

    # Traitement des législatures
    legislatures = df[[
        "legislature_id", "legislature_institution", "legislature_name",
        "legislature_start_date", "legislature_end_date",
        "legislature_wikidata_qid", "legislature_wikipedia_url"
    ]].drop_duplicates("legislature_id")
    legislatures = legislatures.rename(columns={c: c.replace("legislature_", "") for c in legislatures.columns if c != "legislature_id"})

    # Traitement des mandats
    mandates = df[[
        "person_id", "legislature_id", "mandate_position",
        "mandate_group", "mandate_start_date", "mandate_end_date"
    ]].copy()
    mandates.columns = ["person_id", "legislature_id", "position", "group", "start_date", "end_date"]
    mandates["id"] = mandates["person_id"] + "__" + mandates["legislature_id"]
    mandates = mandates.drop_duplicates(subset=["id"])

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM mandates"))
        conn.execute(text("DELETE FROM legislatures"))
        conn.execute(text("DELETE FROM persons"))
        conn.commit()

    persons.to_sql("persons", engine, if_exists="append", index=False)
    legislatures.to_sql("legislatures", engine, if_exists="append", index=False)
    mandates.to_sql("mandates", engine, if_exists="append", index=False)
    print(f"Loaded {len(persons)} persons, {len(legislatures)} legislatures, {len(mandates)} mandates.")

if __name__ == "__main__":
    load_data()