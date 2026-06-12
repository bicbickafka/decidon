"""
routes.py
FastAPI routes for the parlementaires API.
"""

from datetime import date as DateType

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, schemas
from app.index import rebuild_index

api_router = APIRouter()


@api_router.get("/", include_in_schema=False)
async def read_index():
    return FileResponse("app/index.html")


@api_router.get(
    "/persons",
    tags=["persons"],
    summary="Retrieve persons with optional name filters.",
    response_model=list[schemas.PersonOut],
)
def search_persons(
    last_name: str | None = Query(None),
    first_name: str | None = Query(None),
    department: str | None = Query(None),
    group: str | None = Query(None),
    institution: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return crud.search_persons_logic(
        db, last_name, first_name, department, group, institution, limit, offset
    )


@api_router.get(
    "/persons/grouped-mandates",
    tags=["persons"],
    summary="Retrieve persons with grouped mandates.",
    response_model=schemas.PersonMandateGroupSearchResponse,
)
def search_grouped_mandates(
    first_name: str | None = Query(None),
    last_name: str | None = Query(None),
    position: str | None = Query(None),
    group_value: str | None = Query(None),
    mandate_name: str | None = Query(None),
    institution: str | None = Query(None),
    start_from: DateType | None = Query(None),
    end_until: DateType | None = Query(None),
    sort_by: str = Query("last_name"),
    sort_dir: str = Query("asc"),
    limit: int = Query(40, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    total_groups = crud.count_person_mandate_groups_logic(
        db,
        first_name,
        last_name,
        position,
        group_value,
        mandate_name,
        institution,
        start_from,
        end_until,
    )

    items = crud.search_person_mandate_groups_logic(
        db,
        first_name,
        last_name,
        position,
        group_value,
        mandate_name,
        institution,
        start_from,
        end_until,
        sort_by,
        sort_dir,
        limit,
        offset,
    )

    return {
        "total_groups": total_groups,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@api_router.get(
    "/persons/{person_id}",
    tags=["persons"],
    summary="Retrieve a person by person_id.",
    response_model=schemas.PersonDetailOut,
)
def get_person(person_id: str, db: Session = Depends(get_db)):
    result = crud.get_person_by_id(db, person_id)
    if not result:
        raise HTTPException(status_code=404, detail="Person not found")
    return result


@api_router.get(
    "/mandates",
    tags=["mandates"],
    summary="Retrieve mandates with optional filters.",
    response_model=list[schemas.MandateEntityOut],
)
def list_mandates(
    institution: str | None = Query(None),
    name: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return crud.list_mandates_logic(db, institution, name)


@api_router.get(
    "/mandates/{mandate_id}/members",
    tags=["mandates"],
    summary="Retrieve all members of one mandate.",
    response_model=list[schemas.PersonOut],
)
def get_members(mandate_id: str, db: Session = Depends(get_db)):
    return crud.get_members_logic(db, mandate_id)


@api_router.get(
    "/lookup",
    tags=["utils"],
    summary="Fuzzy lookup by person name.",
    response_model=list[schemas.PersonOut],
)
def lookup(
    q: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return crud.lookup_logic(db, q, limit)


@api_router.get(
    "/match",
    tags=["matching"],
    summary="Match one raw Journal officiel mention against persons and mandates.",
    response_model=schemas.MatchResponse,
)
def match_one(
    text: str = Query(...),
    session_date: DateType | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return crud.match_mention_logic(
        db,
        text_value=text,
        session_date=session_date,
        limit=limit,
    )


@api_router.get(
    "/match/rebuild-index",
    tags=["matching"],
    summary="Rebuild the Whoosh index from the SQLite database.",
)
def rebuild_match_index():
    return rebuild_index()