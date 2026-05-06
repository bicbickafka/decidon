"""
models.py
SQLAlchemy ORM models — database layer.
"""
import enum
from typing import Optional
from datetime import date
from sqlalchemy import Column, String, Integer, ForeignKey, Date, Enum, select
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


class AbstractBase:
    """
    Provides a unique Decidon ID automatically generated for URLs.
    Can be inherited by Person, Legislature or Mandate.
    """

    __abstract__ = True
    __prefix__ = None

    @declared_attr
    def decidon_id(cls):
        return Column(
            String(25),
            nullable=False,
            unique=True,
            index=True,
            default=lambda context: cls.generate_unique_id(
                context.connection,
                cls,
                cls.__prefix__
            ),
        )

    @staticmethod
    def generate_unique_id(connection, model_cls, prefix):
        """
        Generate a unique identifier for a model:
        Person      -> PER-000001, PER-000002...
        Legislature -> LEG-000001, LEG-000002...
        Mandate     -> MAN-000001, MAN-000002...
        """

        if prefix is None:
            raise ValueError(
                f"La classe {model_cls.__name__} doit définir un __prefix__"
            )

        table = model_cls.__table__
        column = table.c.decidon_id

        result = connection.execute(
            select(column)
            .where(column.like(f"{prefix}-%"))
            .order_by(column.desc())
            .limit(1)
        ).first()

        if result is None:
            next_number = 1
        else:
            last_id = result[0]
            last_number = int(last_id.replace(f"{prefix}-", ""))
            next_number = last_number + 1

        return f"{prefix}-{next_number:06d}"

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

class Person(AbstractBase, PersonEnrich,Base):
    """Parlementaires et membres du gouvernement."""
    __tablename__ = "persons"
    __prefix__ = "PER"

    person_id: Mapped[str]             = mapped_column(String, primary_key=True)
    last_name: Mapped[str]             = mapped_column(String, nullable=False, index=True)
    first_name: Mapped[str]            = mapped_column(String, nullable=False)
    alias: Mapped[Optional[str]]       = mapped_column(String, nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    death_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    mandates: Mapped[list["Mandate"]]  = relationship(back_populates="person")

    def __repr__(self) -> str:
        return f"<Person {self.person_id} | {self.last_name}, {self.first_name}>"


class Legislature(AbstractBase, AbstractDate, WikiEnrich,Base):
    """Législatures des institutions (chambre, sénat, gouvernement)."""
    __tablename__ = "legislatures"
    __prefix__ = "LEG"

    legislature_id: Mapped[str]          = mapped_column(String, primary_key=True)
    institution: Mapped[InstitutionType] = mapped_column(Enum(InstitutionType), nullable=False)
    name: Mapped[str]                    = mapped_column(String, nullable=False)

    mandates: Mapped[list["Mandate"]]    = relationship(back_populates="legislature")

    def __repr__(self) -> str:
        return f"<Legislature {self.legislature_id} | {self.institution.value} — {self.name}>"


class Mandate(AbstractBase, AbstractDate,Base):
    """Mandats liant une personne à une législature."""
    __tablename__ = "mandates"
    __prefix__ = "MAN"

    id: Mapped[int]                    = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str]             = mapped_column(ForeignKey("persons.person_id"), nullable=False)
    legislature_id: Mapped[str]        = mapped_column(ForeignKey("legislatures.legislature_id"), nullable=False)
    position: Mapped[Optional[str]]    = mapped_column(String, nullable=True)
    group: Mapped[Optional[str]]       = mapped_column(String, nullable=True)

    person: Mapped["Person"]           = relationship(back_populates="mandates")
    legislature: Mapped["Legislature"] = relationship(back_populates="mandates")

    def __repr__(self) -> str:
        return f"<Mandate {self.id} | {self.person_id} @ {self.legislature_id}>"