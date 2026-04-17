from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Imports absolus basés sur le package 'app'
from app.database import engine
from app.models import PersonOut, PersonDetailOut, MandateOut, LegislatureOut

app = FastAPI(
    title="Référentiel des parlementaires et membres du gouvernement sous la IIIe République",
    description="Documentation de l'API",
    version="0.1.0"
)
@app.get("/")
def read_root():
    return {"message": "API opérationnelle"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def db():
    return engine.connect()

# ── 1. Search persons ─────────────────────────────────────────────────────────
@app.get("/persons", response_model=list[PersonOut])
def search_persons(
    last_name:  str | None = Query(None, description="Partial match, case-insensitive"),
    first_name: str | None = Query(None),
    department: str | None = Query(None, description="Filter by mandate position (département)"),
    group:      str | None = Query(None, description="Political group, partial match"),
    institution:str | None = Query(None, description="chambre | senat | gouvernement"),
    limit: int = Query(50, le=500),
    offset: int = Query(0)
):
    filters = ["1=1"]
    params  = {}
    if last_name:
        filters.append("LOWER(p.last_name) LIKE :last_name")
        params["last_name"] = f"%{last_name.lower()}%"
    if first_name:
        filters.append("LOWER(p.first_name) LIKE :first_name")
        params["first_name"] = f"%{first_name.lower()}%"
    if department or group or institution:
        filters.append("p.person_id IN (SELECT person_id FROM mandates m2 "
                       "JOIN legislatures lt2 ON m2.legislature_id = lt2.legislature_id WHERE 1=1"
                       + (" AND LOWER(m2.position) LIKE :dept"  if department  else "")
                       + (" AND LOWER(m2.'group') LIKE :grp"    if group       else "")
                       + (" AND LOWER(lt2.institution) LIKE :inst" if institution else "")
                       + ")")
        if department:  params["dept"] = f"%{department.lower()}%"
        if group:       params["grp"]  = f"%{group.lower()}%"
        if institution: params["inst"] = f"%{institution.lower()}%"

    sql = f"""
        SELECT DISTINCT p.* FROM persons p
        WHERE {' AND '.join(filters)}
        ORDER BY p.last_name, p.first_name
        LIMIT :limit OFFSET :offset
    """
    params.update({"limit": limit, "offset": offset})
    with db() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [PersonOut(**r) for r in rows]

# ── 2. Get one person with all their mandates ─────────────────────────────────
@app.get("/persons/{person_id}", response_model=PersonDetailOut)
def get_person(person_id: str):
    with db() as conn:
        p = conn.execute(
            text("SELECT * FROM persons WHERE person_id = :id"),
            {"id": person_id}
        ).mappings().first()
        if not p:
            raise HTTPException(404, "Person not found")
        mandates = conn.execute(text("""
            SELECT m.*, lt.institution, lt.name AS legislature_name
            FROM mandates m
            JOIN legislatures lt ON m.legislature_id = lt.legislature_id
            WHERE m.person_id = :id
            ORDER BY m.start_date
        """), {"id": person_id}).mappings().all()
    return PersonDetailOut(**p, mandates=[MandateOut(**m) for m in mandates])

# ── 3. List all legislatures ──────────────────────────────────────────────────
@app.get("/legislatures", response_model=list[LegislatureOut])
def list_legislatures(institution: str | None = Query(None)):
    sql = "SELECT * FROM legislatures"
    params = {}
    if institution:
        sql += " WHERE LOWER(institution) LIKE :inst"
        params["inst"] = f"%{institution.lower()}%"
    sql += " ORDER BY start_date"
    with db() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [LegislatureOut(**r) for r in rows]

# ── 4. All members of one legislature ────────────────────────────────────────
@app.get("/legislatures/{legislature_id}/members", response_model=list[PersonOut])
def get_members(legislature_id: str):
    with db() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT p.* FROM persons p
            JOIN mandates m ON p.person_id = m.person_id
            WHERE m.legislature_id = :lid
            ORDER BY p.last_name
        """), {"lid": legislature_id}).mappings().all()
    return [PersonOut(**r) for r in rows]

# ── 5. Fuzzy name lookup ──────────────────────────────────────────────────────
@app.get("/lookup", response_model=list[PersonOut])
def lookup(
    q: str = Query(..., description="Name as it appears in the JO, e.g. 'Léopold Thézard'"),
    limit: int = Query(10, le=50)
):
    parts = q.strip().split()
    conditions, params = [], {}
    for i, part in enumerate(parts):
        key = f"p{i}"
        conditions.append(
            f"(LOWER(last_name) LIKE :{key} OR LOWER(first_name) LIKE :{key})"
        )
        params[key] = f"%{part.lower()}%"
    where = " AND ".join(conditions) if conditions else "1=1"
    params.update({"limit": limit})
    with db() as conn:
        rows = conn.execute(
            text(f"SELECT * FROM persons WHERE {where} ORDER BY last_name LIMIT :limit"),
            params
        ).mappings().all()
    return [PersonOut(**r) for r in rows]