"""
models.py
SQLAlchemy ORM models — database layer.
"""
import enum
from typing import Optional
from datetime import date
from sqlalchemy import Column, String, Integer, ForeignKey, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr
from app.database import Base


###########################################################
# ~~~~~~~~~~~~~~~~~~~ > Enums < ~~~~~~~~~~~~~~~~~~~~~~~~~ #

class InstitutionType(enum.Enum):
    chambre      = "chambre"
    senat        = "senat"
    gouvernement = "gouvernement"


###########################################################
# ~~~~~~~~~~~~~~~~~~~ > Mixins < ~~~~~~~~~~~~~~~~~~~~~~~~ #

class AbstractDate:
    """Mixin providing start_date / end_date columns.
    Used by Legislature and Mandate.
    """
    @declared_attr
    def start_date(cls) -> Mapped[Optional[date]]:
        return mapped_column(Date, nullable=True)

    @declared_attr
    def end_date(cls) -> Mapped[Optional[date]]:
        return mapped_column(Date, nullable=True)


class WikiEnrich:
    """Mixin providing Wikidata / Wikipedia enrichment columns.
    Used by Person and Legislature.
    """
    @declared_attr
    def wikidata_qid(cls) -> Mapped[Optional[str]]:
        return mapped_column(String(25), nullable=True)

    @declared_attr
    def wikipedia_url(cls) -> Mapped[Optional[str]]:
        return mapped_column(String, nullable=True)


class PersonEnrich(WikiEnrich):
    """Mixin extending WikiEnrich with person-specific external identifiers.
    Used by Person.
    """
    @declared_attr
    def sycomore_id(cls) -> Mapped[Optional[str]]:
        return mapped_column(String(25), nullable=True)

    @declared_attr
    def senat_id(cls) -> Mapped[Optional[str]]:
        return mapped_column(String(25), nullable=True)


###########################################################
# ~~~~~~~~~~~~~~~~~~~ > Models < ~~~~~~~~~~~~~~~~~~~~~~~~ #

class Person(Base, PersonEnrich):
    """Parlementaires et membres du gouvernement."""
    __tablename__ = "persons"

    person_id: Mapped[str]             = mapped_column(String, primary_key=True)
    last_name: Mapped[str]             = mapped_column(String, nullable=False, index=True)
    first_name: Mapped[str]            = mapped_column(String, nullable=False)
    alias: Mapped[Optional[str]]       = mapped_column(String, nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    death_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    mandates: Mapped[list["Mandate"]]  = relationship(back_populates="person")

    def __repr__(self) -> str:
        return f"<Person {self.person_id} | {self.last_name}, {self.first_name}>"


class Legislature(Base, AbstractDate, WikiEnrich):
    """Législatures des institutions (chambre, sénat, gouvernement)."""
    __tablename__ = "legislatures"

    legislature_id: Mapped[str]          = mapped_column(String, primary_key=True)
    institution: Mapped[InstitutionType] = mapped_column(Enum(InstitutionType), nullable=False)
    name: Mapped[str]                    = mapped_column(String, nullable=False)

    mandates: Mapped[list["Mandate"]]    = relationship(back_populates="legislature")

    def __repr__(self) -> str:
        return f"<Legislature {self.legislature_id} | {self.institution.value} — {self.name}>"


class Mandate(Base, AbstractDate):
    """Mandats liant une personne à une législature."""
    __tablename__ = "mandates"

    id: Mapped[int]                    = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str]             = mapped_column(ForeignKey("persons.person_id"), nullable=False)
    legislature_id: Mapped[str]        = mapped_column(ForeignKey("legislatures.legislature_id"), nullable=False)
    position: Mapped[Optional[str]]    = mapped_column(String, nullable=True)
    group: Mapped[Optional[str]]       = mapped_column(String, nullable=True)

    person: Mapped["Person"]           = relationship(back_populates="mandates")
    legislature: Mapped["Legislature"] = relationship(back_populates="mandates")

    def __repr__(self) -> str:
        return f"<Mandate {self.id} | {self.person_id} @ {self.legislature_id}>"