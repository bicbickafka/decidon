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

from sqlalchemy import String, Integer, Float, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr, Session

from app.database import Base


###########################################################
# ~~~~~~~~~~~~~~~~~~~ > ID utilities < ~~~~~~~~~~~~~~~~~~ #

def generate_random_uuid(prefix: str, provider: str = "") -> str:
    uuid_bytes = uuid.uuid4().bytes
    base64_encoded = base64.urlsafe_b64encode(uuid_bytes).decode("utf-8").rstrip("=")
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
    pk_col = cls.__mapper__.primary_key[0].name
    while True:
        new_id = generate_random_uuid(prefix=prefix, provider=provider)
        if not session.query(cls).filter(getattr(cls, pk_col) == new_id).first():
            return new_id


###########################################################
# ~~~~~~~~~~~~~~~~~~~ > Enums < ~~~~~~~~~~~~~~~~~~~~~~~~~ #

class InstitutionType(enum.Enum):
    chambre = "chambre"
    senat = "senat"
    gouvernement = "gouvernement"


###########################################################
# ~~~~~~~~~~~~~~~~~~~ > Mixins < ~~~~~~~~~~~~~~~~~~~~~~~~ #

class AbstractDate:
    @declared_attr
    def start_date(cls) -> Mapped[Optional[date]]:
        return mapped_column(String(25), nullable=True)

    @declared_attr
    def end_date(cls) -> Mapped[Optional[date]]:
        return mapped_column(String(25), nullable=True)


class WikiEnrich:
    @declared_attr
    def wikidata_qid(cls) -> Mapped[Optional[str]]:
        return mapped_column(String(25), nullable=True)

    @declared_attr
    def wikipedia_url(cls) -> Mapped[Optional[str]]:
        return mapped_column(String, nullable=True)


class PersonEnrich(WikiEnrich):
    @declared_attr
    def sycomore_id(cls) -> Mapped[Optional[str]]:
        return mapped_column(String(25), nullable=True)

    @declared_attr
    def senat_id(cls) -> Mapped[Optional[str]]:
        return mapped_column(String(25), nullable=True)


###########################################################
# ~~~~~~~~~~~~~~~~~~~ > Models < ~~~~~~~~~~~~~~~~~~~~~~~~ #

class Person(Base, PersonEnrich):
    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    person_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    last_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    alias: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    birth_date: Mapped[Optional[date]] = mapped_column(String(25), nullable=True)
    death_date: Mapped[Optional[date]] = mapped_column(String(25), nullable=True)

    mandate_memberships: Mapped[list["IsMemberOfMandate"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )
    session_links: Mapped[list["IsRelatedToSession"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        if "person_id" not in kwargs:
            kwargs["person_id"] = generate_random_uuid("person", "decidon")
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Person {self.person_id} | {self.last_name}, {self.first_name}>"


class Mandate(Base, AbstractDate, WikiEnrich):
    __tablename__ = "mandates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    mandate_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    institution: Mapped[InstitutionType] = mapped_column(Enum(InstitutionType), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    members: Mapped[list["IsMemberOfMandate"]] = relationship(
        back_populates="mandate",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        if "mandate_id" not in kwargs:
            kwargs["mandate_id"] = generate_random_uuid("mandate", "decidon")
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Mandate {self.mandate_id} | {self.institution.value} — {self.name}>"


class IsMemberOfMandate(Base, AbstractDate):
    __tablename__ = "is_member_of_mandate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.person_id"), nullable=False, index=True)
    mandate_id: Mapped[str] = mapped_column(ForeignKey("mandates.mandate_id"), nullable=False, index=True)
    position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    group: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    person: Mapped["Person"] = relationship(back_populates="mandate_memberships")
    mandate: Mapped["Mandate"] = relationship(back_populates="members")

    def __repr__(self) -> str:
        return f"<IsMemberOfMandate {self.id} | {self.person_id} @ {self.mandate_id}>"


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    institution: Mapped[str] = mapped_column(String, nullable=False)
    ark: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    date: Mapped[Optional[str]] = mapped_column(String(25), nullable=True, index=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pagination_first: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pagination_last: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    related_persons: Mapped[list["IsRelatedToSession"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        if "session_id" not in kwargs:
            kwargs["session_id"] = generate_random_uuid("session", "decidon")
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Session {self.session_id} | {self.institution} — {self.date}>"


class IsRelatedToSession(Base):
    __tablename__ = "is_related_to_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False, index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.person_id"), nullable=False, index=True)
    role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    link_method: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="related_persons")
    person: Mapped["Person"] = relationship(back_populates="session_links")

    def __repr__(self) -> str:
        return f"<IsRelatedToSession {self.id} | {self.person_id} @ {self.session_id}>"