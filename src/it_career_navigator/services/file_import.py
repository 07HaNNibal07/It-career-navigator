import csv
import io
import json
from dataclasses import dataclass

from pydantic import ValidationError

from it_career_navigator.schemas import VacancyImportItem


@dataclass
class ParsedVacancyFile:
    items: list[VacancyImportItem]
    errors: list[str]


def parse_vacancy_file(filename: str | None, content: bytes) -> ParsedVacancyFile:
    if not filename:
        raise ValueError("Uploaded file must have a name")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("File must be encoded as UTF-8") from error

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension == "json":
        return _parse_json(text)
    if extension == "csv":
        return _parse_csv(text)

    raise ValueError("Only .json and .csv files are supported")


def _parse_json(text: str) -> ParsedVacancyFile:
    try:
        raw_items = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON: {error.msg}") from error

    if not isinstance(raw_items, list):
        raise ValueError("JSON file must contain a list of vacancies")

    return _validate_items(
        raw_items,
        labels=[f"Item {index}" for index in range(1, len(raw_items) + 1)],
    )


def _parse_csv(text: str) -> ParsedVacancyFile:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV file must contain a header row")

    raw_items: list[dict[str, object]] = []
    labels: list[str] = []

    for row_number, row in enumerate(reader, start=2):
        normalized_row: dict[str, object] = {
            key: value if value != "" else None
            for key, value in row.items()
            if key is not None
        }
        requirements_value = normalized_row.get("requirements")

        if requirements_value is None:
            normalized_row["requirements"] = []
        else:
            try:
                normalized_row["requirements"] = json.loads(str(requirements_value))
            except json.JSONDecodeError as error:
                raw_items.append({"_requirements_error": error.msg})
                labels.append(f"Row {row_number}")
                continue

        raw_items.append(normalized_row)
        labels.append(f"Row {row_number}")

    return _validate_items(raw_items, labels=labels)


def _validate_items(
    raw_items: list[object],
    *,
    labels: list[str],
) -> ParsedVacancyFile:
    items: list[VacancyImportItem] = []
    errors: list[str] = []

    for label, raw_item in zip(labels, raw_items, strict=True):
        if isinstance(raw_item, dict) and "_requirements_error" in raw_item:
            errors.append(f"{label}: invalid requirements JSON")
            continue

        try:
            items.append(VacancyImportItem.model_validate(raw_item))
        except ValidationError as error:
            errors.append(f"{label}: {error.errors()[0]['msg']}")

    return ParsedVacancyFile(items=items, errors=errors)
