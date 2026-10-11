from sqlalchemy.orm import relationship, Mapped, mapped_column
from it_career_navigator.database import Base
from sqlalchemy import String

class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    surname: Mapped[str] = mapped_column(String(50))
    age: Mapped[int] = mapped_column()
    email: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20))
    password: Mapped[str] = mapped_column(String(100))