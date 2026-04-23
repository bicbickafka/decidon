from typing import Optional
from datetime import date
from sqlalchemy import String, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Person(Base):
    __tablename__ = "persons"
    person_id: Mapped[str] = mapped_column(String, primary_key=True)
    last_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    alias: Mapped[str] = mapped_column(String, nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    death_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    wikidata_qid: Mapped[str] = mapped_column(String, nullable=True)
    wikipedia_url: Mapped[str] = mapped_column(String, nullable=True)
    sycomore_id: Mapped[str] = mapped_column(String, nullable=True)
    senat_id: Mapped[str] = mapped_column(String, nullable=True)
    mandates: Mapped[list["Mandate"]] = relationship(back_populates="person")

class Legislature(Base):
    __tablename__ = "legislatures"
    legislature_id: Mapped[str] = mapped_column(String, primary_key=True)
    institution: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=False)
    wikidata_qid: Mapped[str] = mapped_column(String, nullable=True)
    wikipedia_url: Mapped[str] = mapped_column(String, nullable=True)
    mandates: Mapped[list["Mandate"]] = relationship(back_populates="legislature")

class Mandate(Base):
    __tablename__ = "mandates"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.person_id"), nullable=False)
    legislature_id: Mapped[str] = mapped_column(ForeignKey("legislatures.legislature_id"), nullable=False)
    position: Mapped[str] = mapped_column(String, nullable=False)
    group: Mapped[str] = mapped_column(String, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    person: Mapped["Person"] = relationship(back_populates="mandates")
    legislature: Mapped["Legislature"] = relationship(back_populates="mandates")