"""
app/crud.py
Contains the data access logic.
"""
from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session

def get_person_by_id(db: Session, person_id: str):
    # Your original working logic
    p = db.execute(text("SELECT * FROM persons WHERE person_id = :id"), {"id": person_id}).mappings().first()
    if not p: return None

    mandates = db.execute(text("""
                               SELECT m.*, lt.institution, lt.name AS legislature_name
                               FROM mandates m
                                        JOIN legislatures lt ON m.legislature_id = lt.legislature_id
                               WHERE m.person_id = :id
                               ORDER BY m.start_date
                               """), {"id": person_id}).mappings().all()

    return {**p, "mandates": mandates}


def search_persons_logic(db: Session, last_name, first_name, department, group, institution, limit, offset):
    # Your original working filtering logic
    filters, params = ["1=1"], {}
    if last_name:
        filters.append("LOWER(p.last_name) LIKE :last_name")
        params["last_name"] = f"%{last_name.lower()}%"
    if first_name:
        filters.append("LOWER(p.first_name) LIKE :first_name")
        params["first_name"] = f"%{first_name.lower()}%"
    if department or group or institution:
        filters.append(
            "p.person_id IN (SELECT person_id FROM mandates m2 JOIN legislatures lt2 ON m2.legislature_id = lt2.legislature_id WHERE 1=1"
            + (" AND LOWER(m2.position) LIKE :dept" if department else "")
            + (" AND LOWER(m2.'group') LIKE :grp" if group else "")
            + (" AND LOWER(lt2.institution) LIKE :inst" if institution else "") + ")")
        if department: params["dept"] = f"%{department.lower()}%"
        if group: params["grp"] = f"%{group.lower()}%"
        if institution: params["inst"] = f"%{institution.lower()}%"

    sql = f"SELECT DISTINCT p.* FROM persons p WHERE {' AND '.join(filters)} ORDER BY p.last_name, p.first_name LIMIT :limit OFFSET :offset"
    params.update({"limit": limit, "offset": offset})
    return db.execute(text(sql), params).mappings().all()


def lookup_logic(db: Session, q: str, limit: int):
    # Your original working fuzzy lookup logic
    parts = q.strip().split()
    conditions, params = [], {}
    for i, part in enumerate(parts):
        key = f"p{i}"
        conditions.append(f"(LOWER(last_name) LIKE :{key} OR LOWER(first_name) LIKE :{key})")
        params[key] = f"%{part.lower()}%"
    where = " AND ".join(conditions) if conditions else "1=1"
    params.update({"limit": limit})
    return db.execute(text(f"SELECT * FROM persons WHERE {where} ORDER BY last_name LIMIT :limit"),
                      params).mappings().all()

def list_legislatures_logic(db: Session, institution: str | None, name: str | None):
    sql = "SELECT * FROM legislatures WHERE 1=1"
    params = {}
    if institution:
        sql += " AND LOWER(institution) LIKE :inst"
        params["inst"] = f"%{institution.lower()}%"
    if name:
        sql += " AND LOWER(name) LIKE :name"
        params["name"] = f"%{name.lower()}%"
    sql += " ORDER BY start_date"
    return db.execute(text(sql), params).mappings().all()

def get_members_logic(db: Session, legislature_id: str):
    sql = """
        SELECT DISTINCT p.* FROM persons p
        JOIN mandates m ON p.person_id = m.person_id
        WHERE m.legislature_id = :lid
        ORDER BY p.last_name
    """
    return db.execute(text(sql), {"lid": legislature_id}).mappings().all()

def get_persons_by_role_at_date(db: Session, position: str, date: date):
    sql = """
        SELECT DISTINCT p.*, m.position, m.group,
               lt.name AS legislature_name, lt.institution
        FROM persons p
        JOIN mandates m ON p.person_id = m.person_id
        JOIN legislatures lt ON m.legislature_id = lt.legislature_id
        WHERE LOWER(m.position) LIKE :position
          AND (m.start_date IS NULL OR m.start_date <= :date)
          AND (m.end_date IS NULL OR m.end_date >= :date)
        ORDER BY p.last_name
    """
    return db.execute(text(sql), {
        "position": f"%{position.lower()}%",
        "date": date
    }).mappings().all()