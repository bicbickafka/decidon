"""
crud.py
Database query logic for the parlementaires API.
"""

from __future__ import annotations

import unicodedata
from datetime import date
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.index import DecidonSearchEngine

DEFAULT_START = "1870-01-01"
DEFAULT_END = "1940-07-10"


def normalize(text_value: Optional[str]) -> str:
    if not text_value:
        return ""
    text_value = text_value.replace("’", "'").strip()
    text_value = unicodedata.normalize("NFD", text_value).encode("ascii", "ignore").decode()
    return " ".join(text_value.lower().split())


def _person_filters(first_name: Optional[str], last_name: Optional[str]) -> tuple[list[str], dict[str, Any]]:
    filters = ["1=1"]
    params: dict[str, Any] = {}

    if first_name:
        filters.append("LOWER(COALESCE(p.first_name, '')) LIKE :first_name")
        params["first_name"] = f"%{normalize(first_name)}%"

    if last_name:
        filters.append("LOWER(COALESCE(p.last_name, '')) LIKE :last_name")
        params["last_name"] = f"%{normalize(last_name)}%"

    return filters, params


def _mandate_filters(
    position: Optional[str],
    group_value: Optional[str],
    mandate_name: Optional[str],
    institution: Optional[str],
    start_from: Optional[date],
    end_until: Optional[date],
) -> tuple[list[str], dict[str, Any]]:
    filters = ["1=1"]
    params: dict[str, Any] = {}

    if position:
        filters.append("LOWER(COALESCE(imm.position, '')) LIKE :position")
        params["position"] = f"%{normalize(position)}%"

    if group_value:
        filters.append('LOWER(COALESCE(imm."group", \'\')) LIKE :group_value')
        params["group_value"] = f"%{normalize(group_value)}%"

    if mandate_name:
        filters.append("LOWER(COALESCE(m.name, '')) LIKE :mandate_name")
        params["mandate_name"] = f"%{normalize(mandate_name)}%"

    if institution:
        filters.append("LOWER(COALESCE(m.institution, '')) LIKE :institution")
        params["institution"] = f"%{normalize(institution)}%"

    if start_from:
        filters.append(
            """
            (
                CASE
                    WHEN LOWER(m.institution) = 'gouvernement'
                        THEN :at_date BETWEEN COALESCE(m.start_date, :default_start)
                                         AND COALESCE(m.end_date, :default_end)
                    ELSE :at_date BETWEEN COALESCE(imm.start_date, :default_start)
                                     AND COALESCE(imm.end_date, :default_end)
                END
            )
            """
        )
        params["at_date"] = start_from.isoformat()
        params["default_start"] = DEFAULT_START
        params["default_end"] = DEFAULT_END

    if end_until:
        filters.append(
            """
            (
                CASE
                    WHEN LOWER(m.institution) = 'gouvernement'
                        THEN COALESCE(m.end_date, :default_end) <= :end_until
                    ELSE COALESCE(imm.end_date, :default_end) <= :end_until
                END
            )
            """
        )
        params["end_until"] = end_until.isoformat()
        params["default_end"] = DEFAULT_END

    return filters, params


def _base_person_mandate_join() -> str:
    return """
        FROM persons p
        JOIN is_member_of_mandate imm ON imm.person_id = p.person_id
        JOIN mandates m ON m.mandate_id = imm.mandate_id
    """


def count_person_mandate_groups_logic(
    db: Session,
    first_name: Optional[str],
    last_name: Optional[str],
    position: Optional[str],
    group_value: Optional[str],
    mandate_name: Optional[str],
    institution: Optional[str],
    start_from: Optional[date],
    end_until: Optional[date],
) -> int:
    p_filters, p_params = _person_filters(first_name, last_name)
    m_filters, m_params = _mandate_filters(
        position, group_value, mandate_name, institution, start_from, end_until
    )
    params = {**p_params, **m_params}

    sql = f"""
        SELECT COUNT(*) FROM (
            SELECT p.person_id
            {_base_person_mandate_join()}
            WHERE {' AND '.join(p_filters)} AND {' AND '.join(m_filters)}
            GROUP BY p.person_id
        ) grouped_people
    """

    return int(db.execute(text(sql), params).scalar_one())


def search_person_mandate_groups_logic(
    db: Session,
    first_name: Optional[str],
    last_name: Optional[str],
    position: Optional[str],
    group_value: Optional[str],
    mandate_name: Optional[str],
    institution: Optional[str],
    start_from: Optional[date],
    end_until: Optional[date],
    sort_by: str,
    sort_dir: str,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    p_filters, p_params = _person_filters(first_name, last_name)
    m_filters, m_params = _mandate_filters(
        position, group_value, mandate_name, institution, start_from, end_until
    )
    params = {**p_params, **m_params}

    allowed_sort_by = {"last_name": "p.last_name", "first_name": "p.first_name"}
    order_col = allowed_sort_by.get(sort_by, "p.last_name")
    order_dir = "DESC" if str(sort_dir).lower() == "desc" else "ASC"

    people_sql = f"""
        SELECT
            p.person_id,
            p.last_name,
            p.first_name,
            p.alias,
            p.birth_date,
            p.death_date,
            p.wikidata_qid,
            p.wikipedia_url,
            p.sycomore_id,
            p.senat_id
        {_base_person_mandate_join()}
        WHERE {' AND '.join(p_filters)} AND {' AND '.join(m_filters)}
        GROUP BY
            p.person_id, p.last_name, p.first_name, p.alias,
            p.birth_date, p.death_date, p.wikidata_qid,
            p.wikipedia_url, p.sycomore_id, p.senat_id
        ORDER BY {order_col} {order_dir}
        LIMIT :limit OFFSET :offset
    """

    people = db.execute(
        text(people_sql),
        {**params, "limit": limit, "offset": offset},
    ).mappings().all()

    results: list[dict[str, Any]] = []

    for person in people:
        mandates_sql = f"""
            SELECT
                m.mandate_id,
                LOWER(m.institution) AS institution,
                m.name AS mandate_name,
                imm.position,
                imm.role,
                imm."group" AS "group",
                imm.start_date,
                imm.end_date
            FROM is_member_of_mandate imm
            JOIN mandates m ON m.mandate_id = imm.mandate_id
            WHERE imm.person_id = :person_id AND {' AND '.join(m_filters)}
            ORDER BY COALESCE(imm.start_date, m.start_date) ASC
        """

        mandates = db.execute(
            text(mandates_sql),
            {**m_params, "person_id": person["person_id"]},
        ).mappings().all()

        results.append(
            {
                "person": dict(person),
                "mandates": [dict(m) for m in mandates],
            }
        )

    return results


def get_person_by_id(db: Session, person_id: str) -> Optional[dict[str, Any]]:
    person_sql = """
        SELECT
            p.person_id,
            p.last_name,
            p.first_name,
            p.alias,
            p.birth_date,
            p.death_date,
            p.wikidata_qid,
            p.wikipedia_url,
            p.sycomore_id,
            p.senat_id
        FROM persons p
        WHERE p.person_id = :person_id
    """
    person = db.execute(text(person_sql), {"person_id": person_id}).mappings().first()

    if not person:
        return None

    mandates_sql = """
        SELECT
            m.mandate_id,
            LOWER(m.institution) AS institution,
            m.name AS mandate_name,
            imm.position,
            imm.role,
            imm."group" AS "group",
            imm.start_date,
            imm.end_date
        FROM is_member_of_mandate imm
        JOIN mandates m ON m.mandate_id = imm.mandate_id
        WHERE imm.person_id = :person_id
        ORDER BY COALESCE(imm.start_date, m.start_date) ASC
    """
    mandates = db.execute(text(mandates_sql), {"person_id": person_id}).mappings().all()

    return {
        **dict(person),
        "mandates": [dict(m) for m in mandates],
    }


def search_persons_logic(
    db: Session,
    last_name: Optional[str],
    first_name: Optional[str],
    department: Optional[str],
    group: Optional[str],
    institution: Optional[str],
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    filters = ["1=1"]
    params: dict[str, Any] = {}

    if last_name:
        filters.append("LOWER(COALESCE(p.last_name, '')) LIKE :last_name")
        params["last_name"] = f"%{normalize(last_name)}%"

    if first_name:
        filters.append("LOWER(COALESCE(p.first_name, '')) LIKE :first_name")
        params["first_name"] = f"%{normalize(first_name)}%"

    sql = f"""
        SELECT
            p.person_id,
            p.last_name,
            p.first_name,
            p.alias,
            p.birth_date,
            p.death_date,
            p.wikidata_qid,
            p.wikipedia_url,
            p.sycomore_id,
            p.senat_id
        FROM persons p
        WHERE {' AND '.join(filters)}
        ORDER BY p.last_name ASC, p.first_name ASC
        LIMIT :limit OFFSET :offset
    """

    return [
        dict(row)
        for row in db.execute(
            text(sql),
            {**params, "limit": limit, "offset": offset},
        ).mappings().all()
    ]


def get_persons_by_role_at_date(db: Session, position: str, at_date: date) -> list[dict[str, Any]]:
    sql = """
        SELECT DISTINCT
            p.person_id,
            p.last_name,
            p.first_name,
            p.alias,
            p.birth_date,
            p.death_date,
            p.wikidata_qid,
            p.wikipedia_url,
            p.sycomore_id,
            p.senat_id
        FROM persons p
        JOIN is_member_of_mandate imm ON imm.person_id = p.person_id
        JOIN mandates m ON m.mandate_id = imm.mandate_id
        WHERE LOWER(COALESCE(imm.position, '')) LIKE :position
          AND (
                CASE
                    WHEN LOWER(m.institution) = 'gouvernement'
                        THEN :at_date BETWEEN COALESCE(m.start_date, :default_start)
                                         AND COALESCE(m.end_date, :default_end)
                    ELSE :at_date BETWEEN COALESCE(imm.start_date, :default_start)
                                     AND COALESCE(imm.end_date, :default_end)
                END
              )
        ORDER BY p.last_name ASC, p.first_name ASC
    """

    return [
        dict(row)
        for row in db.execute(
            text(sql),
            {
                "position": f"%{normalize(position)}%",
                "at_date": at_date.isoformat(),
                "default_start": DEFAULT_START,
                "default_end": DEFAULT_END,
            },
        ).mappings().all()
    ]


def list_mandates_logic(
    db: Session,
    institution: Optional[str],
    name: Optional[str],
) -> list[dict[str, Any]]:
    filters = ["1=1"]
    params: dict[str, Any] = {}

    if institution:
        filters.append("LOWER(COALESCE(institution, '')) LIKE :institution")
        params["institution"] = f"%{normalize(institution)}%"

    if name:
        filters.append("LOWER(COALESCE(name, '')) LIKE :name")
        params["name"] = f"%{normalize(name)}%"

    sql = f"""
        SELECT
            mandate_id,
            institution,
            name,
            start_date,
            end_date,
            wikidata_qid,
            wikipedia_url
        FROM mandates
        WHERE {' AND '.join(filters)}
        ORDER BY start_date ASC
    """

    return [dict(row) for row in db.execute(text(sql), params).mappings().all()]


def get_members_logic(db: Session, mandate_id: str) -> list[dict[str, Any]]:
    sql = """
        SELECT DISTINCT
            p.person_id,
            p.last_name,
            p.first_name,
            p.alias,
            p.birth_date,
            p.death_date,
            p.wikidata_qid,
            p.wikipedia_url,
            p.sycomore_id,
            p.senat_id
        FROM persons p
        JOIN is_member_of_mandate imm ON imm.person_id = p.person_id
        WHERE imm.mandate_id = :mandate_id
        ORDER BY p.last_name ASC, p.first_name ASC
    """

    return [
        dict(row)
        for row in db.execute(text(sql), {"mandate_id": mandate_id}).mappings().all()
    ]


def lookup_logic(db: Session, q: str, limit: int) -> list[dict[str, Any]]:
    q_norm = normalize(q)

    sql = """
        SELECT
            person_id,
            last_name,
            first_name,
            alias,
            birth_date,
            death_date,
            wikidata_qid,
            wikipedia_url,
            sycomore_id,
            senat_id
        FROM persons
        WHERE LOWER(COALESCE(last_name, '')) LIKE :q
           OR LOWER(COALESCE(first_name, '')) LIKE :q
           OR LOWER(COALESCE(alias, '')) LIKE :q
        ORDER BY last_name ASC, first_name ASC
        LIMIT :limit
    """

    return [
        dict(row)
        for row in db.execute(
            text(sql),
            {"q": f"%{q_norm}%", "limit": limit},
        ).mappings().all()
    ]


def match_mention_logic(db, text_value: str, session_date=None, limit: int = 5):
    engine = DecidonSearchEngine()
    try:
        return engine.search(query_str=text_value, session_date=session_date, limit=limit)
    finally:
        engine.close()