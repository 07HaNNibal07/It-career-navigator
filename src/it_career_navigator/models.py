from sqlalchemy.orm import relationship, Mapped, mapped_column
from it_career_navigator.database import Base
from sqlalchemy import String, ForeignKey


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
    