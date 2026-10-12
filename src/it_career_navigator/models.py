from sqlalchemy.orm import relationship, Mapped, mapped_column
from it_career_navigator.database import Base
from sqlalchemy import String, ForeignKey

class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    surname: Mapped[str] = mapped_column(String(50))
    age: Mapped[int] = mapped_column()
    email: Mapped[str] = mapped_column(String(100), unique=True)
    phone: Mapped[str] = mapped_column(String(20))
    password: Mapped[str] = mapped_column(String(100))
    skills: Mapped[list["PersonSkills"]] = relationship(back_populates="person")
    
class Skills(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    persons: Mapped[list["PersonSkills"]] = relationship(back_populates="skill")
    
class PersonSkills(Base):
    __tablename__ = "person_skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id", ondelete="CASCADE"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    person: Mapped["Person"] = relationship(back_populates="skills")
    skill: Mapped["Skills"] = relationship(back_populates="persons")