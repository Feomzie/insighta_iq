from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import math

from app.dependencies.version import require_api_version
from app.services.profiles_services import get_profiles, search_profiles_nlp
from app.db.database import get_db

import csv
import io
from fastapi.responses import StreamingResponse
from datetime import datetime


router = APIRouter(prefix="/api/profiles")

#LIST
@router.get("/")
def list_profiles(
    request: Request,
    gender: str = None,
    age_group: str = None,
    country_id: str = None,
    min_age: int = None,
    max_age: int = None,
    sort_by: str = None,
    order: str = "asc",
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_version)
):
    limit = max(limit, 1)

    total, results = get_profiles(
        db=db,
        gender=gender,
        age_group=age_group,
        country_id=country_id,
        min_age=min_age,
        max_age=max_age,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit
    )


    #PAGINATION
    total_pages = math.ceil(total / limit)

    base = str(request.url).split("?")[0]

    links = {
        "self": f"{base}?page={page}&limit={limit}",
        "next": f"{base}?page={page+1}&limit={limit}" if page < total_pages else None,
        "prev": f"{base}?page={page-1}&limit={limit}" if page > 1 else None,
    }

    data = [
        {
            "id": p.id,
            "name": p.name,
            "gender": p.gender,
            "gender_probability": p.gender_probability,
            "age": p.age,
            "age_group": p.age_group,
            "country_id": p.country_id,
            "country_name": p.country_name,
            "country_probability": p.country_probability,
            "created_at": str(p.created_at)
        }
        for p in results
    ]

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "links": links,
        "data": data
    }


#SEARCH
@router.get("/search")
def search_profiles(
    request: Request,
    q: str,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_version)
):

    result = search_profiles_nlp(db, q, page, limit)

    if result is None:
        return {
            "status": "error",
            "message": "Invalid query"
        }
    limit = max(limit, 1)

    total, results = result

    #PAGINATION
    total_pages = math.ceil(total / limit)

    base = str(request.base_url) + "api/profiles"

    links = {
        "self": f"{base}?q={q}&page={page}&limit={limit}",
        "next": f"{base}?q={q}&page={page+1}&limit={limit}" if page < total_pages else None,
        "prev": f"{base}?q={q}&page={page-1}&limit={limit}" if page > 1 else None,
    }

    data = [
        {
            "id": p.id,
            "name": p.name,
            "gender": p.gender,
            "gender_probability": p.gender_probability,
            "age": p.age,
            "age_group": p.age_group,
            "country_id": p.country_id,
            "country_name": p.country_name,
            "country_probability": p.country_probability,
            "created_at": str(p.created_at)
        }
        for p in results
    ]

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "links": links,
        "data": data
    }

#CSV EXPORT
@router.get("/export")
def export_profiles(
    request: Request,
    gender: str = None,
    age_group: str = None,
    country_id: str = None,
    min_age: int = None,
    max_age: int = None,
    sort_by: str = None,
    order: str = "asc",
    db: Session = Depends(get_db),
    _: None = Depends(require_api_version)
):

    total, results = get_profiles(
        db=db,
        gender=gender,
        age_group=age_group,
        country_id=country_id,
        min_age=min_age,
        max_age=max_age,
        sort_by=sort_by,
        order=order,
        page=1,
        limit=1000
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id", "name", "gender", "gender_probability",
        "age", "age_group", "country_id", "country_name",
        "country_probability", "created_at"
    ])

    for p in results:
        writer.writerow([
            p.id,
            p.name,
            p.gender,
            p.gender_probability,
            p.age,
            p.age_group,
            p.country_id,
            p.country_name,
            p.country_probability,
            p.created_at
        ])

    output.seek(0)

    filename = f"profiles_{datetime.utcnow().timestamp()}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

