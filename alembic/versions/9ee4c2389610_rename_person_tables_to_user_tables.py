"""rename person tables to user tables

Revision ID: 9ee4c2389610
Revises: ad3651a9b1ec
Create Date: 2026-10-14 22:32:55.677407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ee4c2389610'
down_revision: Union[str, Sequence[str], None] = 'ad3651a9b1ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("persons", "users")

    op.alter_column(
        "person_skills",
        "person_id",
        new_column_name="user_id",
    )

    op.rename_table("person_skills", "user_skills")


def downgrade() -> None:
    op.rename_table("user_skills", "person_skills")

    op.alter_column(
        "person_skills",
        "user_id",
        new_column_name="person_id",
    )

    op.rename_table("users", "persons")
