from fastapi import APIRouter, HTTPException, Query, Request

from it_career_navigator.auth import CurrentUser
from it_career_navigator.database import Get_DB
from it_career_navigator.letter_schemas import CoverLetterResponse, CoverLetterUpdate
from it_career_navigator.routers.pages import page_context, redirect, require_user, templates
from it_career_navigator.services import cover_letters as service
from it_career_navigator.services.career_profile import validate

router = APIRouter(prefix="/users", tags=["cover letters"])
pages_router = APIRouter(include_in_schema=False)


@router.post("/vacancy_matches/{match_id}/cover_letters", response_model=CoverLetterResponse, status_code=201)
async def generate(match_id: int, current_user: CurrentUser, db: Get_DB):
    return await service.generate(current_user["id"], match_id, db)


@router.get("/cover_letters", response_model=list[CoverLetterResponse])
async def history(current_user: CurrentUser, db: Get_DB,
                  offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    return await service.history(current_user["id"], db, offset, limit)


@router.get("/cover_letters/{letter_id}", response_model=CoverLetterResponse)
async def detail(letter_id: int, current_user: CurrentUser, db: Get_DB):
    return await service.get_letter(current_user["id"], letter_id, db)


@router.patch("/cover_letters/{letter_id}", response_model=CoverLetterResponse)
async def edit(letter_id: int, data: CoverLetterUpdate, current_user: CurrentUser, db: Get_DB):
    return await service.edit(current_user["id"], letter_id, data, db)


@pages_router.post("/vacancies/matches/{match_id}/cover-letter")
async def generate_page(match_id: int, request: Request, db: Get_DB):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")
    try:
        letter = await service.generate(user.id, match_id, db)
    except HTTPException as error:
        if error.status_code not in (422, 502, 503):
            raise
        return templates.TemplateResponse(request, "letter_error.html", page_context(
            request, user=user, error=error.detail, match_id=match_id,
        ), status_code=error.status_code)
    return redirect(f"/cover-letters/{letter.id}")


@pages_router.get("/cover-letters")
async def history_page(request: Request, db: Get_DB, offset: int = Query(0, ge=0)):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")
    letters = await service.history(user.id, db, offset, 21)
    return templates.TemplateResponse(request, "cover_letters.html", page_context(
        request, user=user, letters=letters[:20], offset=offset, has_more=len(letters) > 20,
    ))


@pages_router.get("/cover-letters/{letter_id}")
async def letter_page(letter_id: int, request: Request, db: Get_DB, saved: bool = False):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")
    letter = await service.get_letter(user.id, letter_id, db)
    return templates.TemplateResponse(request, "cover_letter.html", page_context(request, user=user, letter=letter, saved=saved))


@pages_router.post("/cover-letters/{letter_id}")
async def edit_page(letter_id: int, request: Request, db: Get_DB):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")
    letter = await service.get_letter(user.id, letter_id, db)
    form = await request.form()
    submitted = str(form.get("edited_text", ""))
    try:
        data = validate(CoverLetterUpdate, {"edited_text": submitted, "version": form.get("version")})
        await service.edit(user.id, letter_id, data, db)
    except HTTPException as error:
        if error.status_code not in (409, 422):
            raise
        message = error.detail if isinstance(error.detail, str) else "Письмо должно содержать от 1 до 20 000 символов."
        return templates.TemplateResponse(request, "cover_letter.html", page_context(
            request, user=user, letter=letter, error=message, submitted_text=submitted,
        ), status_code=error.status_code)
    return redirect(f"/cover-letters/{letter_id}?saved=true")
