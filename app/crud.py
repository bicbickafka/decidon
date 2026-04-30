"""
crud.py
Database query logic for the parlementaires API.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import date
import unicodedata


def normalize(text_value: str) -> str:
    if not text_value:
        return text_value
    return unicodedata.normalize("NFD", text_value).encode("ascii", "ignore").decode().lower()


def _mandate_filters(position, group_value, legislature_name, institution, start_from, end_until):
    filters = ["1=1"]
    params = {}
    if position:
        filters.append("LOWER(COALESCE(m.position, '')) LIKE :position")
        params["position"] = f"%{normalize(position)}%"
    if group_value:
        filters.append('LOWER(COALESCE(m."group", \'\')) LIKE :group_value')
        params["group_value"] = f"%{normalize(group_value)}%"
    if legislature_name:
        filters.append("LOWER(lt.name) LIKE :legislature_name")
        params["legislature_name"] = f"%{normalize(legislature_name)}%"
    if institution:
        filters.append("LOWER(lt.institution) LIKE :institution")
        params["institution"] = f"%{normalize(institution)}%"
    if start_from:
        filters.append(":at_date BETWEEN COALESCE(m.start_date, '1870-01-01') AND COALESCE(m.end_date, '1940-07-10')")
        params["at_date"] = start_from
    if end_until:
        filters.append("(m.end_date IS NOT NULL AND m.end_date <= :end_until)")
        params["end_until"] = end_until
    return filters, params


def _person_filters(first_name, last_name):
    filters = ["1=1"]
    params = {}
    if first_name:
        filters.append("LOWER(COALESCE(p.first_name, '')) LIKE :first_name")
        params["first_name"] = f"%{normalize(first_name)}%"
    if last_name:
        filters.append("LOWER(p.last_name) LIKE :last_name")
        params["last_name"] = f"%{normalize(last_name)}%"
    return filters, params


# ── Grouped mandates (list view) ──────────────────────────────────────────────

def count_person_mandate_groups_logic(db: Session, first_name, last_name, position, group_value,
                                      legislature_name, institution, start_from, end_until):
    p_filters, p_params = _person_filters(first_name, last_name)
    m_filters, m_params = _mandate_filters(position, group_value, legislature_name, institution, start_from, end_until)
    params = {**p_params, **m_params}
    sql = f"""
        SELECT COUNT(*) FROM (
            SELECT p.person_id FROM persons p
            JOIN mandates m ON m.person_id = p.person_id
            JOIN legislatures lt ON lt.legislature_id = m.legislature_id
            WHERE {' AND '.join(p_filters)} AND {' AND '.join(m_filters)}
            GROUP BY p.person_id
        ) t
    """
    return db.execute(text(sql), params).scalar_one()


def search_person_mandate_groups_logic(db: Session, first_name, last_name, position, group_value,
                                       legislature_name, institution, start_from, end_until,
                                       sort_by, sort_dir, limit, offset):
    p_filters, p_params = _person_filters(first_name, last_name)
    m_filters, m_params = _mandate_filters(position, group_value, legislature_name, institution, start_from, end_until)
    params = {**p_params, **m_params}

    order_col = "p.last_name" if sort_by == "last_name" else "p.first_name"
    order_dir = "DESC" if str(sort_dir).lower() == "desc" else "ASC"

    group_sql = f"""
        SELECT p.* FROM persons p
        JOIN mandates m ON m.person_id = p.person_id
        JOIN legislatures lt ON lt.legislature_id = m.legislature_id
        WHERE {' AND '.join(p_filters)} AND {' AND '.join(m_filters)}
        GROUP BY p.person_id
        ORDER BY {order_col} {order_dir} LIMIT :limit OFFSET :offset
    """
    people = db.execute(text(group_sql), {**params, "limit": limit, "offset": offset}).mappings().all()

    results = []
    for p in people:
        mandate_sql = f"""
            SELECT m.*, lt.name as legislature_name, lt.institution FROM mandates m
            JOIN legislatures lt ON m.legislature_id = lt.legislature_id
            WHERE m.person_id = :pid AND {' AND '.join(m_filters)}
            ORDER BY m.start_date ASC
        """
        mandates = db.execute(text(mandate_sql), {**m_params, "pid": p["person_id"]}).mappings().all()
        results.append({"person": dict(p), "mandates": [dict(m) for m in mandates]})
    return results


# ── Person detail (permalink view) ───────────────────────────────────────────

def get_person_by_id(db: Session, person_id: str):
    """Fetch a single person with all their mandates by person_id."""
    person_sql = """
        SELECT * FROM persons WHERE person_id = :person_id
    """
    person = db.execute(text(person_sql), {"person_id": person_id}).mappings().first()
    if not person:
        return None

    mandate_sql = """
        SELECT m.*, lt.name as legislature_name, lt.institution
        FROM mandates m
        JOIN legislatures lt ON m.legislature_id = lt.legislature_id
        WHERE m.person_id = :person_id
        ORDER BY m.start_date ASC
    """
    mandates = db.execute(text(mandate_sql), {"person_id": person_id}).mappings().all()

    return {
        **dict(person),
        "mandates": [dict(m) for m in mandates]
    }


# ── Remaining route logic ─────────────────────────────────────────────────────

def search_persons_logic(db: Session, last_name, first_name, department, group, institution, limit, offset):
    filters = ["1=1"]
    params = {}
    if last_name:
        filters.append("LOWER(p.last_name) LIKE :last_name")
        params["last_name"] = f"%{normalize(last_name)}%"
    if first_name:
        filters.append("LOWER(COALESCE(p.first_name, '')) LIKE :first_name")
        params["first_name"] = f"%{normalize(first_name)}%"
    sql = f"""
        SELECT * FROM persons p
        WHERE {' AND '.join(filters)}
        ORDER BY p.last_name ASC
        LIMIT :limit OFFSET :offset
    """
    return db.execute(text(sql), {**params, "limit": limit, "offset": offset}).mappings().all()


def get_persons_by_role_at_date(db: Session, position: str, date: date):
    sql = """
        SELECT p.* FROM persons p
        JOIN mandates m ON m.person_id = p.person_id
        WHERE LOWER(COALESCE(m.position, '')) LIKE :position
          AND :at_date BETWEEN COALESCE(m.start_date, '1870-01-01') AND COALESCE(m.end_date, '1940-07-10')
    """
    return db.execute(text(sql), {"position": f"%{normalize(position)}%", "at_date": date}).mappings().all()


def list_legislatures_logic(db: Session, institution, name):
    filters = ["1=1"]
    params = {}
    if institution:
        filters.append("LOWER(institution) LIKE :institution")
        params["institution"] = f"%{normalize(institution)}%"
    if name:
        filters.append("LOWER(name) LIKE :name")
        params["name"] = f"%{normalize(name)}%"
    sql = f"SELECT * FROM legislatures WHERE {' AND '.join(filters)} ORDER BY start_date ASC"
    return db.execute(text(sql), params).mappings().all()


def get_members_logic(db: Session, legislature_id: str):
    sql = """
        SELECT DISTINCT p.* FROM persons p
        JOIN mandates m ON m.person_id = p.person_id
        WHERE m.legislature_id = :legislature_id
        ORDER BY p.last_name ASC
    """
    return db.execute(text(sql), {"legislature_id": legislature_id}).mappings().all()


def lookup_logic(db: Session, q: str, limit: int):
    sql = """
        SELECT * FROM persons
        WHERE LOWER(last_name) LIKE :q OR LOWER(COALESCE(first_name, '')) LIKE :q
        ORDER BY last_name ASC
        LIMIT :limit
    """
    return db.execute(text(sql), {"q": f"%{normalize(q)}%", "limit": limit}).mappings().all()