"""
models.py
SQLAlchemy ORM models — database layer.
"""
import enum
import uuid
import base64
import random
import string
from typing import Optional
from datetime import date
from sqlalchemy import Column, String, Integer, ForeignKey, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr, Session
from app.database import Base


###########################################################
# ~~~~~~~~~~~~~~~~~~~ > ID utilities < ~~~~~~~~~~~~~~~~~~ #

def generate_random_uuid(prefix: str, provider: str = "") -> str:
    """Generates a random UUID and converts it to a URL-safe Base64 encoded
    bytes string and decoded to a Unicode string.

    :param prefix: The prefix to use for the generated ID (e.g., "person" or "legislature").
    :type prefix: str
    :param provider: An optional provider string to include in the generated ID (e.g., "decidon"), defaults to an empty string.
    :type provider: str, optional
    :returns: A unique identifier string combining the prefix, provider, and a random component derived from a UUID.
    :rtype: str
    """
    uuid_bytes = uuid.uuid4().bytes
    base64_encoded = base64.urlsafe_b64encode(uuid_bytes).decode("utf-8").rstrip("=")
    # replace punctuation with random characters
    # cut uuid to 8 (but possibility to increase or decrease)
    # this represents ≈ 10,376,800,670,380,293 possible identifier combinations
    random_chars = "".join(
        random.choice(string.ascii_letters) if c in string.punctuation else c
        for c in base64_encoded[:8]
    )
    return (
        f"{prefix}_{provider}_{random_chars}"
        if provider
        else f"{prefix}_{random_chars}"
    )


def generate_unique_id(session: Session, cls: any, prefix: str, provider: str = "decidon") -> str:
    """Generate a unique identifier for a given class by creating random UUIDs
    and checking for uniqueness in the database session.

    :param session: The database session to use for checking uniqueness.
    :type session: Session
    :param cls: The class for which to generate the unique identifier (e.g., Person or Legislature).
    :type cls: any
    :param prefix: The prefix to use for the generated identifier (e.g., "person" or "legislature").
    :type prefix: str
    :param provider: The provider string to include in the generated ID. Defaults to "decidon".
    :type provider: str, optional
    :returns: A unique identifier string that does not already exist in the database for the specified class.
    :rtype: str
    """
    pk_col = cls.__mapper__.primary_key[0].name
    while True:
        new_id = generate_random_uuid(prefix=prefix, provider=provider)
        if not session.query(cls).filter(getattr(cls, pk_col) == new_id).first():
            return new_id


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
        return mapped_column(String(25), nullable=True)

    @declared_attr
    def end_date(cls) -> Mapped[Optional[date]]:
        return mapped_column(String(25), nullable=True)


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

    id: Mapped[str]                         = mapped_column(String, primary_key=True)
    person_id: Mapped[str]                  = mapped_column(String, nullable=False, unique=True, index=True)
    last_name: Mapped[str]                  = mapped_column(String, nullable=False, index=True)
    first_name: Mapped[str]                 = mapped_column(String, nullable=False, index=True)
    alias: Mapped[Optional[str]]            = mapped_column(String, nullable=True, index=True)
    birth_date: Mapped[Optional[date]]      = mapped_column(String(25), nullable=True)
    death_date: Mapped[Optional[date]]      = mapped_column(String(25), nullable=True)

    mandates: Mapped[list["Mandate"]]       = relationship(back_populates="person")

    def __init__(self, **kwargs):
        if "person_id" not in kwargs:
            kwargs["person_id"] = generate_random_uuid("person", "decidon")
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Person {self.person_id} | {self.last_name}, {self.first_name}>"


class Legislature(Base, AbstractDate, WikiEnrich):
    """Législatures des institutions (chambre, sénat, gouvernement)."""
    __tablename__ = "legislatures"

    id: Mapped[str]                              = mapped_column(String, primary_key=True)
    legislature_id: Mapped[str]                  = mapped_column(String, nullable=False, unique=True, index=True)
    institution: Mapped[InstitutionType]         = mapped_column(Enum(InstitutionType), nullable=False)
    name: Mapped[str]                            = mapped_column(String, nullable=False)

    mandates: Mapped[list["Mandate"]]            = relationship(back_populates="legislature")

    def __init__(self, **kwargs):
        if "legislature_id" not in kwargs:
            kwargs["legislature_id"] = generate_random_uuid("legislature", "decidon")
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Legislature {self.legislature_id} | {self.institution.value} — {self.name}>"


class Mandate(Base, AbstractDate):
    """Mandats liant une personne à une législature."""
    __tablename__ = "mandates"

    id: Mapped[int]                          = mapped_column(Integer, primary_key=True, autoincrement=True)
    mandate_id: Mapped[str]                  = mapped_column(String, nullable=False, unique=True)
    person_id: Mapped[str]                   = mapped_column(ForeignKey("persons.person_id"), nullable=False)
    legislature_id: Mapped[str]              = mapped_column(ForeignKey("legislatures.legislature_id"), nullable=False)
    position: Mapped[Optional[str]]          = mapped_column(String, nullable=True)
    role: Mapped[Optional[str]]              = mapped_column(String, nullable=True)
    constituency: Mapped[Optional[str]]      = mapped_column(String, nullable=True)
    group: Mapped[Optional[str]]             = mapped_column(String, nullable=True)

    person: Mapped["Person"]                 = relationship(back_populates="mandates")
    legislature: Mapped["Legislature"]       = relationship(back_populates="mandates")

    def __repr__(self) -> str:
        return f"<Mandate {self.id} | {self.person_id} @ {self.legislature_id}>"