import csv
import io
import json

import pytest
from sqlalchemy import select

from it_career_navigator.models import Vacancy

pytestmark = pytest.mark.anyio
KEY = {"X-Internal-API-Key": "test-internal-key"}
BASE = {"source": "conditions", "external_id": "001", "title": "Python Developer", "description": "Python"}
CONDITIONS = {"city": "Москва", "work_format": "remote", "employment_type": "full_time", "min_experience_months": 0}


async def test_create_vacancy_preserves_work_conditions(client, db_session):
    response = await client.post("/internal/create_vacancy", headers=KEY, json=BASE | CONDITIONS)
    assert response.status_code == 200, response.text
    assert all(response.json()[key] == value for key, value in CONDITIONS.items())
    vacancy = (await db_session.scalars(select(Vacancy))).one()
    assert vacancy.min_experience_months == 0
    assert vacancy.city == "Москва"


async def test_old_vacancy_payload_keeps_unknown_conditions(client):
    response = await client.post("/internal/create_vacancy", headers=KEY, json=BASE)
    assert response.status_code == 200
    assert all(response.json()[key] is None for key in CONDITIONS)


@pytest.mark.parametrize("field,value", [
    ("min_experience_months", -1), ("min_experience_months", 1.5),
    ("min_experience_months", True), ("work_format", "whatever"),
    ("employment_type", "whatever"), ("city", "x" * 101),
])
async def test_invalid_conditions_are_rejected(client, field, value):
    response = await client.post("/internal/create_vacancy", headers=KEY, json=BASE | {field: value})
    assert response.status_code == 422


@pytest.mark.parametrize("extension", ["json", "csv"])
async def test_import_conditions_legacy_fields_and_error_report(client, db_session, extension):
    await client.post("/internal/create_directions", headers=KEY, json={"name": "Python Backend"})
    rows = [
        BASE | CONDITIONS | {"direction_name": "Python Backend"},
        BASE | {"external_id": "002", "direction_name": "Python Backend"},
        BASE | {"external_id": "003", "direction_name": "Python Backend", "min_experience_months": -12},
    ]
    if extension == "json":
        content = json.dumps(rows).encode()
    else:
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        content = stream.getvalue().encode()
    response = await client.post("/internal/import_vacancies_file", headers=KEY,
                                 files={"file": ("conditions." + extension, content)})
    assert response.status_code == 200, response.text
    assert response.json()["created_vacancies"] == 2
    assert len(response.json()["errors"]) == 1
    vacancies = (await db_session.scalars(select(Vacancy).order_by(Vacancy.external_id))).all()
    assert vacancies[0].min_experience_months == 0
    assert all(getattr(vacancies[0], key) == value for key, value in CONDITIONS.items())
    assert all(getattr(vacancies[1], key) is None for key in CONDITIONS)
    # The existing source/external_id rule still skips duplicate vacancies.
    response = await client.post("/internal/import_vacancies_file", headers=KEY,
                                 files={"file": ("conditions." + extension, content)})
    assert response.json()["created_vacancies"] == 0
    assert response.json()["skipped_duplicates"] == 2
