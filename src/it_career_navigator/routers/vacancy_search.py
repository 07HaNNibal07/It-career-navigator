from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select

from it_career_navigator.auth import CurrentUser
from it_career_navigator.career_schemas import EMPLOYMENT_TYPES, WORK_FORMATS
from it_career_navigator.database import Get_DB
from it_career_navigator.matching_schemas import (
    VacancyMatchResponse, VacancySearchCreate, VacancySearchDetails, VacancySearchResponse,
)
from it_career_navigator.models import Direction, VacancySearch
from it_career_navigator.routers.pages import page_context, redirect, require_user, templates
from it_career_navigator.services import matching
from it_career_navigator.services.career_profile import get_user, validate

router = APIRouter(prefix="/users", tags=["vacancy matching"])
pages_router = APIRouter(include_in_schema=False)


@router.post("/vacancy_searches", response_model=VacancySearchResponse, status_code=201)
async def create_search(data: VacancySearchCreate, current_user: CurrentUser, db: Get_DB):
    return await matching.create_search(current_user["id"], data, db)


@router.get("/vacancy_searches", response_model=list[VacancySearchResponse])
async def history(current_user: CurrentUser, db: Get_DB,
                  offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    await get_user(current_user["id"], db)
    return (await db.scalars(select(VacancySearch).where(VacancySearch.user_id == current_user["id"])
        .order_by(VacancySearch.created_at.desc(), VacancySearch.id.desc()).offset(offset).limit(limit))).all()


@router.get("/vacancy_searches/{search_id}", response_model=VacancySearchDetails)
async def results(search_id: int, current_user: CurrentUser, db: Get_DB,
                  offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    return await matching.search_results(current_user["id"], search_id, db, offset, limit)


@router.get("/vacancy_matches/{match_id}", response_model=VacancyMatchResponse)
async def match_detail(match_id: int, current_user: CurrentUser, db: Get_DB):
    return await matching.get_match(current_user["id"], match_id, db)


@pages_router.get("/vacancies")
async def vacancies_page(request: Request, db: Get_DB, offset: int = Query(0, ge=0)):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")
    history = (await db.scalars(select(VacancySearch).where(VacancySearch.user_id == user.id)
        .order_by(VacancySearch.created_at.desc(), VacancySearch.id.desc()).offset(offset).limit(21))).all()
    directions = (await db.scalars(select(Direction).order_by(Direction.name))).all()
    return templates.TemplateResponse(request, "vacancies.html", page_context(
        request, user=user, directions=directions, history=history[:20], offset=offset,
        has_more=len(history) > 20, work_formats=WORK_FORMATS, employment_types=EMPLOYMENT_TYPES,
    ))


@pages_router.post("/vacancies/searches")
async def create_search_page(request: Request, db: Get_DB):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")
    form = await request.form()
    try:
        data = validate(VacancySearchCreate, {
            "desired_position": form.get("desired_position") or None,
            "city": form.get("city") or None,
            "direction_id": form.get("direction_id") or None,
            "target_level": form.get("target_level") or None,
            "work_formats": form.getlist("work_formats"),
            "employment_types": form.getlist("employment_types"),
            "include_unknown_conditions": form.get("include_unknown_conditions") == "on",
        })
        search = await matching.create_search(user.id, data, db)
    except HTTPException as error:
        if error.status_code != 422:
            raise
        message = error.detail if isinstance(error.detail, str) else "Проверь параметры подбора."
        return templates.TemplateResponse(request, "career_error.html", page_context(request, user=user, error=message), status_code=422)
    return redirect(f"/vacancies/searches/{search.id}")


@pages_router.get("/vacancies/searches/{search_id}")
async def search_page(search_id: int, request: Request, db: Get_DB, offset: int = Query(0, ge=0)):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")
    data = await matching.search_results(user.id, search_id, db, offset)
    return templates.TemplateResponse(request, "vacancy_results.html", page_context(request, user=user, offset=offset, **data))


@pages_router.get("/vacancies/matches/{match_id}")
async def match_page(match_id: int, request: Request, db: Get_DB):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")
    match = await matching.get_match(user.id, match_id, db)
    search = await matching.get_search(user.id, match.search_id, db)
    # Legacy imports permit arbitrary URLs. Only HTTP(S) links are clickable.
    url = match.vacancy_snapshot.get("url") or ""
    safe_url = url if url.lower().startswith(("https://", "http://")) else None
    return templates.TemplateResponse(request, "vacancy_match.html", page_context(
        request, user=user, match=match, search=search, safe_url=safe_url,
        work_formats=WORK_FORMATS, employment_types=EMPLOYMENT_TYPES,
    ))
