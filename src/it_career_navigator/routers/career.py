from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from it_career_navigator.auth import CurrentUser
from it_career_navigator.career_schemas import (
    CareerPreferencesUpdate, CareerProfileResponse, ExperienceCreate, ExperienceResponse,
    ExperienceUpdate, ProjectCreate, ProjectResponse, ProjectUpdate,
)
from it_career_navigator.database import Get_DB
from it_career_navigator.models import UserExperience, UserProject
from it_career_navigator.routers.pages import redirect, require_user, templates
from it_career_navigator.services import career_profile as service


router = APIRouter(prefix="/users/career_profile", tags=["career profile"])
pages_router = APIRouter(include_in_schema=False)


@router.get("", response_model=CareerProfileResponse)
async def profile(current_user: CurrentUser, db: Get_DB):
    return await service.get_profile(current_user["id"], db)


@router.patch("", response_model=CareerProfileResponse)
async def preferences(data: CareerPreferencesUpdate, current_user: CurrentUser, db: Get_DB):
    return await service.save_preferences(current_user["id"], data, db)


@router.get("/experiences", response_model=list[ExperienceResponse])
async def experiences(current_user: CurrentUser, db: Get_DB):
    return (await service.get_profile(current_user["id"], db)).experiences


@router.post("/experiences", response_model=ExperienceResponse, status_code=201)
async def create_experience(data: ExperienceCreate, current_user: CurrentUser, db: Get_DB):
    return await service.save_experience(current_user["id"], data, db)


@router.patch("/experiences/{item_id}", response_model=ExperienceResponse)
async def update_experience(item_id: int, data: ExperienceUpdate, current_user: CurrentUser, db: Get_DB):
    return await service.save_experience(current_user["id"], data, db, item_id)


@router.delete("/experiences/{item_id}", status_code=204)
async def delete_experience(item_id: int, current_user: CurrentUser, db: Get_DB):
    await service.delete_record(UserExperience, item_id, current_user["id"], db)
    return Response(status_code=204)


@router.get("/projects", response_model=list[ProjectResponse])
async def projects(current_user: CurrentUser, db: Get_DB):
    return (await service.get_profile(current_user["id"], db)).projects


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, current_user: CurrentUser, db: Get_DB):
    return await service.save_project(current_user["id"], data, db)


@router.patch("/projects/{item_id}", response_model=ProjectResponse)
async def update_project(item_id: int, data: ProjectUpdate, current_user: CurrentUser, db: Get_DB):
    return await service.save_project(current_user["id"], data, db, item_id)


@router.delete("/projects/{item_id}", status_code=204)
async def delete_project(item_id: int, current_user: CurrentUser, db: Get_DB):
    await service.delete_record(UserProject, item_id, current_user["id"], db)
    return Response(status_code=204)


async def handle_form(request, db, section, item_id=None, delete=False):
    """All HTML forms use the same validated services as the JSON API."""
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")
    if item_id is not None:
        model = UserExperience if section == "experiences" else UserProject
        await service.get_owned(model, item_id, user.id, db)
    form = await request.form()
    if delete:
        model = UserExperience if section == "experiences" else UserProject
        await service.delete_record(model, item_id, user.id, db)
    elif section == "preferences":
        data = service.validate(CareerPreferencesUpdate, {
            "desired_position": form.get("desired_position"), "city": form.get("city"),
            "work_formats": form.getlist("work_formats"),
            "employment_types": form.getlist("employment_types"),
        })
        await service.save_preferences(user.id, data, db)
    elif section == "experiences":
        data = service.validate(ExperienceCreate, {
            "position": form.get("position"), "organization": form.get("organization"),
            "start_date": form.get("start_date"), "end_date": form.get("end_date") or None,
            "description": form.get("description", ""), "achievements": form.get("achievements", ""),
        })
        await service.save_experience(user.id, data, db, item_id)
    else:
        data = service.validate(ProjectCreate, {
            "name": form.get("name"), "description": form.get("description", ""),
            "role": form.get("role"), "url": form.get("url") or None,
            "skill_ids": form.getlist("skill_ids"),
            "skill_names": [value for value in form.getlist("skill_names") if value.strip()],
        })
        await service.save_project(user.id, data, db, item_id)
    return redirect(f"/profile#{section}")


async def form_result(request, db, section, item_id=None, delete=False):
    from fastapi import HTTPException
    try:
        return await handle_form(request, db, section, item_id, delete)
    except HTTPException as error:
        if error.status_code != 422:
            raise
        await db.rollback()
        message = error.detail
        if isinstance(message, list):
            message = "; ".join(str(item.get("msg", "Некорректное значение")) for item in message)
        # Keep entered fields in the browser; navigation back restores the form.
        return templates.TemplateResponse(request, "career_error.html", {
            "request": request, "user": await require_user(request, db), "error": message,
        }, status_code=422)


@pages_router.post("/profile/preferences", response_class=HTMLResponse)
async def preferences_form(request: Request, db: Get_DB):
    return await form_result(request, db, "preferences")


@pages_router.post("/profile/experiences")
async def experience_form(request: Request, db: Get_DB):
    return await form_result(request, db, "experiences")


@pages_router.post("/profile/experiences/{item_id}")
async def experience_edit_form(item_id: int, request: Request, db: Get_DB):
    return await form_result(request, db, "experiences", item_id)


@pages_router.post("/profile/experiences/{item_id}/delete")
async def experience_delete_form(item_id: int, request: Request, db: Get_DB):
    return await form_result(request, db, "experiences", item_id, delete=True)


@pages_router.post("/profile/projects")
async def project_form(request: Request, db: Get_DB):
    return await form_result(request, db, "projects")


@pages_router.post("/profile/projects/{item_id}")
async def project_edit_form(item_id: int, request: Request, db: Get_DB):
    return await form_result(request, db, "projects", item_id)


@pages_router.post("/profile/projects/{item_id}/delete")
async def project_delete_form(item_id: int, request: Request, db: Get_DB):
    return await form_result(request, db, "projects", item_id, delete=True)
