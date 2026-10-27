from datetime import datetime,UTC

from sqlalchemy.orm import relationship, Mapped, mapped_column
from it_career_navigator.database import Base
from sqlalchemy import DateTime, ForeignKey,String,Text,UniqueConstraint


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    surname: Mapped[str] = mapped_column(String(50))
    age: Mapped[int] = mapped_column()
    email: Mapped[str] = mapped_column(String(100), unique=True)
    phone: Mapped[str] = mapped_column(String(20))
    password: Mapped[str] = mapped_column(String(100))
    skills: Mapped[list["UserSkill"]] = relationship(back_populates="user")
    direction_id: Mapped[int | None] = mapped_column(ForeignKey("directions.id", ondelete="SET NULL"), nullable=True)
    target_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    direction: Mapped["Direction | None"] = relationship(back_populates="users")
    
    
class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    users: Mapped[list["UserSkill"]] = relationship(back_populates="skill")
    vacancy_requirements: Mapped[list["VacancyRequirement"]] = relationship(back_populates="skill")
    aliases: Mapped[list["SkillAlias"]] = relationship(back_populates="skill")
    
class UserSkill(Base):
    __tablename__ = "user_skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(back_populates="users")


class Direction(Base):
    __tablename__ = "directions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    users: Mapped[list["User"]] = relationship(back_populates="direction")
    vacancies: Mapped[list["Vacancy"]] = relationship(back_populates="direction")

class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    source: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(100))

    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str | None] = mapped_column(String(150), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    
    description: Mapped[str] = mapped_column(Text)

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    direction_id: Mapped[int | None] = mapped_column(
        ForeignKey("directions.id", ondelete="SET NULL"),
        nullable=True,
    )
    level: Mapped[str | None] = mapped_column(String(30), nullable=True)

    direction: Mapped["Direction | None"] = relationship(
        back_populates="vacancies"
    )
    requirements: Mapped[list["VacancyRequirement"]] = relationship(back_populates="vacancy")
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_vacancies_source_external_id",
        ),
    )

class VacancyRequirement(Base):
    __tablename__ = "vacancy_requirements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    is_required: Mapped[bool] = mapped_column(default=True)
    
    vacancy: Mapped["Vacancy"] = relationship(back_populates="requirements")
    skill: Mapped["Skill"] = relationship(back_populates="vacancy_requirements")
    
    __table_args__ = (
        UniqueConstraint(
            "vacancy_id",
            "skill_id",
            name="uq_vacancy_requirements_vacancy_id_skill_id",
        ),
    )
    
class SkillAlias(Base):
    __tablename__ = "skill_aliases"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alias: Mapped[str] = mapped_column(String(100), unique=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    skill: Mapped["Skill"] = relationship(back_populates="aliases")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    direction_id: Mapped[int] = mapped_column(ForeignKey("directions.id", ondelete="CASCADE"))
    target_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str | None] = mapped_column(String(30), default='queued')
    
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

