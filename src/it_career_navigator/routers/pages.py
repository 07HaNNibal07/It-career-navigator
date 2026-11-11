from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from it_career_navigator.auth import hash_password, verify_password
from it_career_navigator.database import Get_DB
from it_career_navigator.models import (
    Analysis,
    Direction,
    Roadmap,
    RoadmapItem,
    Skill,
    SkillStatistic,
    User,
    UserSkill,
)
from it_career_navigator.services.analysis import run_analysis
from it_career_navigator.services.roadmap import build_roadmap


templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)
router = APIRouter(include_in_schema=False)


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


async def current_user(request: Request, db: AsyncSession) -> User | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None

    result = await db.execute(
        select(User)
        .options(selectinload(User.skills).selectinload(UserSkill.skill))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def require_user(request: Request, db: AsyncSession) -> User | None:
    user = await current_user(request, db)
    if user is None:
        request.session.clear()
    return user


def page_context(request: Request, **context: object) -> dict[str, object]:
    return {"request": request, **context}


@router.get("/")
async def home(request: Request, db: Get_DB):
    user = await current_user(request, db)
    return templates.TemplateResponse(
        request,
        "home.html",
        page_context(request, user=user),
    )


@router.get("/register")
async def register_page(request: Request, db: Get_DB):
    if await current_user(request, db):
        return redirect("/profile")
    return templates.TemplateResponse(request, "register.html", page_context(request))


@router.post("/register")
async def register(
    request: Request,
    db: Get_DB,
    name: str = Form(),
    surname: str = Form(),
    email: str = Form(),
    age: int = Form(),
    phone: str = Form(),
    password: str = Form(),
):
    existing_user = await db.execute(select(User).where(User.email == email))
    if existing_user.scalar_one_or_none():
        return templates.TemplateResponse(
            request,
            "register.html",
            page_context(request, error="Пользователь с таким email уже существует."),
            status_code=400,
        )

    user = User(
        name=name,
        surname=surname,
        email=email,
        age=age,
        phone=phone,
        password=hash_password(password),
    )
    db.add(user)
    await db.commit()
    return redirect("/login")


@router.get("/login")
async def login_page(request: Request, db: Get_DB):
    if await current_user(request, db):
        return redirect("/profile")
    return templates.TemplateResponse(request, "login.html", page_context(request))


@router.post("/login")
async def login(
    request: Request,
    db: Get_DB,
    email: str = Form(),
    password: str = Form(),
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password):
        return templates.TemplateResponse(
            request,
            "login.html",
            page_context(request, error="Неверный email или пароль."),
            status_code=401,
        )

    request.session["user_id"] = user.id
    return redirect("/profile")


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return redirect("/")


@router.get("/profile")
async def profile(request: Request, db: Get_DB):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    directions = (await db.execute(select(Direction).order_by(Direction.name))).scalars().all()
    return templates.TemplateResponse(
        request,
        "profile.html",
        page_context(request, user=user, directions=directions),
    )


@router.post("/profile/target")
async def update_target(
    request: Request,
    db: Get_DB,
    direction_id: int = Form(),
    target_level: str = Form(),
):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    direction = await db.execute(select(Direction).where(Direction.id == direction_id))
    if direction.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Direction not found")

    user.direction_id = direction_id
    user.target_level = target_level
    await db.commit()
    return redirect("/profile")


@router.post("/profile/skills")
async def add_skill(
    request: Request,
    db: Get_DB,
    name: str = Form(),
    proficiency_level: str = Form(),
):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    skill_result = await db.execute(select(Skill).where(Skill.name == name))
    skill = skill_result.scalar_one_or_none()
    if skill is None:
        skill = Skill(name=name)
        db.add(skill)
        await db.flush()

    user_skill_result = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == user.id,
            UserSkill.skill_id == skill.id,
        )
    )
    user_skill = user_skill_result.scalar_one_or_none()
    if user_skill is None:
        db.add(
            UserSkill(
                user_id=user.id,
                skill_id=skill.id,
                proficiency_level=proficiency_level,
            )
        )
    else:
        user_skill.proficiency_level = proficiency_level

    await db.commit()
    return redirect("/profile")


@router.post("/profile/skills/{skill_id}/level")
async def update_skill_level(
    skill_id: int,
    request: Request,
    db: Get_DB,
    proficiency_level: str = Form(),
):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    result = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == user.id,
            UserSkill.skill_id == skill_id,
        )
    )
    user_skill = result.scalar_one_or_none()
    if user_skill is None:
        raise HTTPException(status_code=404, detail="User skill not found")

    user_skill.proficiency_level = proficiency_level
    await db.commit()
    return redirect("/profile")


@router.post("/profile/skills/{skill_id}/delete")
async def delete_skill(skill_id: int, request: Request, db: Get_DB):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    result = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == user.id,
            UserSkill.skill_id == skill_id,
        )
    )
    user_skill = result.scalar_one_or_none()
    if user_skill is not None:
        await db.delete(user_skill)
        await db.commit()

    return redirect("/profile")


@router.get("/analyses")
async def analyses_page(request: Request, db: Get_DB):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    directions = (await db.execute(select(Direction).order_by(Direction.name))).scalars().all()
    analyses = (
        await db.execute(
            select(Analysis)
            .where(Analysis.user_id == user.id)
            .order_by(Analysis.created_at.desc())
        )
    ).scalars().all()
    return templates.TemplateResponse(
        request,
        "analyses.html",
        page_context(request, user=user, directions=directions, analyses=analyses),
    )


@router.post("/analyses")
async def create_analysis_page(
    request: Request,
    db: Get_DB,
    direction_id: int = Form(),
    target_level: str = Form(),
):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    analysis = Analysis(
        user_id=user.id,
        direction_id=direction_id,
        target_level=target_level or None,
        status="queued",
        created_at=datetime.now(UTC),
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return redirect(f"/analyses/{analysis.id}")


@router.get("/analyses/{analysis_id}")
async def analysis_page(analysis_id: int, request: Request, db: Get_DB):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user.id,
        )
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    statistics = (
        await db.execute(
            select(SkillStatistic, Skill.name)
            .join(Skill, Skill.id == SkillStatistic.skill_id)
            .where(SkillStatistic.analysis_id == analysis.id)
            .order_by(SkillStatistic.demand_percent.desc())
        )
    ).all()
    roadmap = (
        await db.execute(select(Roadmap).where(Roadmap.analysis_id == analysis.id))
    ).scalar_one_or_none()
    return templates.TemplateResponse(
        request,
        "analysis.html",
        page_context(
            request,
            user=user,
            analysis=analysis,
            statistics=statistics,
            roadmap=roadmap,
        ),
    )


@router.post("/analyses/{analysis_id}/run")
async def run_analysis_page(analysis_id: int, request: Request, db: Get_DB):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    try:
        await run_analysis(analysis_id, user.id, db)
    except HTTPException:
        return redirect(f"/analyses/{analysis_id}")
    return redirect(f"/analyses/{analysis_id}")


@router.post("/analyses/{analysis_id}/roadmap")
async def build_roadmap_page(analysis_id: int, request: Request, db: Get_DB):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    roadmap = await build_roadmap(analysis_id, user.id, db)
    return redirect(f"/roadmaps/{roadmap.id}")


@router.get("/roadmaps/{roadmap_id}")
async def roadmap_page(roadmap_id: int, request: Request, db: Get_DB):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    roadmap_result = await db.execute(
        select(Roadmap)
        .join(Analysis, Analysis.id == Roadmap.analysis_id)
        .where(Roadmap.id == roadmap_id, Analysis.user_id == user.id)
    )
    roadmap = roadmap_result.scalar_one_or_none()
    if roadmap is None:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    items = (
        await db.execute(
            select(RoadmapItem, Skill.name)
            .join(Skill, Skill.id == RoadmapItem.skill_id)
            .where(RoadmapItem.roadmap_id == roadmap.id)
            .order_by(RoadmapItem.priority.desc())
        )
    ).all()
    return templates.TemplateResponse(
        request,
        "roadmap.html",
        page_context(request, user=user, roadmap=roadmap, items=items),
    )


@router.post("/roadmap-items/{roadmap_item_id}/toggle")
async def toggle_roadmap_item(
    roadmap_item_id: int,
    request: Request,
    db: Get_DB,
):
    user = await require_user(request, db)
    if user is None:
        return redirect("/login")

    result = await db.execute(
        select(RoadmapItem, Roadmap.id)
        .join(Roadmap, Roadmap.id == RoadmapItem.roadmap_id)
        .join(Analysis, Analysis.id == Roadmap.analysis_id)
        .where(
            RoadmapItem.id == roadmap_item_id,
            Analysis.user_id == user.id,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Roadmap item not found")

    item, roadmap_id = row
    item.is_completed = not item.is_completed
    await db.commit()
    return redirect(f"/roadmaps/{roadmap_id}")
