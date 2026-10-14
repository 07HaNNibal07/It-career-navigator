# IT Career Navigator

[English](README.md) | [Русский](README.ru.md)

IT Career Navigator is an asynchronous FastAPI backend for an IT career-planning system. The current version provides the foundation for user accounts, a personal skill profile, JWT-protected user actions, and API-key-protected internal skill-catalog operations.

The project is being developed as a diploma project. Its target product will help a user compare their skills with IT vacancy requirements and receive a prioritized learning roadmap. Vacancy import, market analysis, LLM extraction, and the web interface are planned features; they are not part of the current API yet.

## Goals

- provide a secure backend for an IT career profile;
- let a user register, sign in, view and update their profile, and manage personal skills;
- separate user-facing JWT access from trusted internal API operations;
- establish a testable async FastAPI/SQLAlchemy base for the later vacancy-analysis workflow.

## Implemented features

- User registration with unique email validation and Argon2 password hashing.
- OAuth2 password-flow login that returns a Bearer JWT.
- Authenticated profile retrieval and update.
- Authenticated user deletion.
- Adding and removing skills from the authenticated user's profile.
- A shared skill catalog with a many-to-many `Person`--`Skills` relation through `PersonSkills`.
- Internal endpoints protected by the `X-Internal-API-Key` header for creating and clearing catalog skills.
- Async SQLAlchemy access through SQLite and `aiosqlite`.
- API tests for core user flows and internal API-key access.

## Technology stack

| Area | Technology |
| --- | --- |
| Language | Python 3.14+ |
| Web framework | FastAPI |
| Validation and settings | Pydantic v2, pydantic-settings |
| ORM | SQLAlchemy 2.x, async sessions |
| Current database driver | SQLite with aiosqlite |
| Password hashing | pwdlib with Argon2 |
| Token handling | PyJWT, OAuth2 Bearer scheme |
| Testing | pytest, AnyIO, HTTPX ASGI transport |
| Dependency management | uv |

## Project structure

```text
.
├── .env.example
├── PLAN.md
├── pyproject.toml
├── README.md
├── README.ru.md
└── src/
    └── it_career_navigator/
        ├── auth.py          # Password, JWT, and internal API-key dependencies
        ├── config.py        # Environment-based settings
        ├── database.py      # Async engine, session, and declarative base
        ├── main.py          # FastAPI application and lifespan setup
        ├── models.py        # SQLAlchemy models
        ├── schemas.py       # Pydantic request and response schemas
        ├── routers/
        │   ├── internal.py  # Trusted internal API
        │   └── users.py     # User API
        └── tests/
            ├── conftest.py
            ├── test_internal.py
            └── test_user.py
```

## Prerequisites

- Python 3.14 or newer, as declared in `pyproject.toml`.
- [uv](https://docs.astral.sh/uv/) installed.

## Installation

Clone the repository and enter its directory:

```bash
git clone <repository-url>
cd it-career-navigator
```

Install the locked project dependencies and create the virtual environment:

```bash
uv sync
```

## Configuration

Create a local `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Fill in the variables in `.env`:

```dotenv
db_url=sqlite+aiosqlite:///./it_career_navigator.db
secret_key=replace-with-a-long-random-secret-of-at-least-32-characters
algorithm=HS256
access_token_expire_minutes=30
internal_api_key=replace-with-a-separate-internal-key
```

| Variable | Required | Purpose |
| --- | --- | --- |
| `db_url` | Yes | SQLAlchemy database URL. The current implementation uses an async SQLite URL. |
| `secret_key` | Yes | Secret used to sign and validate JWTs. Do not commit it. |
| `algorithm` | No | JWT algorithm; defaults to `HS256`. |
| `access_token_expire_minutes` | No | JWT lifetime in minutes; defaults to `30`. |
| `internal_api_key` | Recommended | Key required by internal catalog endpoints. |

Never commit `.env` or real secrets.

## Running the application

Start the FastAPI development server from the repository root:

```bash
uv run fastapi dev src/it_career_navigator/main.py
```

The API will be available at `http://127.0.0.1:8000`. Interactive OpenAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

On application startup, the current SQLAlchemy metadata is created in the configured database. The project does not use migrations yet.

## Tests

Run the user API tests:

```bash
uv run pytest src/it_career_navigator/tests/test_user.py -v
```

Run internal API tests:

```bash
uv run pytest src/it_career_navigator/tests/test_internal.py -v
```

The tests configure their own SQLite URL and test-only JWT/API-key values in `tests/conftest.py` before application imports.

> Current test-suite note: `pytest_plugins = ["anyio"]` is declared in the nested `src/it_career_navigator/tests/conftest.py`. With pytest 9, running `uv run pytest -v` from the repository root can fail during collection because that declaration must be top-level. The file-specific commands above are the currently documented commands. Moving or removing that declaration is a planned test-configuration cleanup.

## API overview

### Public and user endpoints

| Method | Path | Access | Description |
| --- | --- | --- | --- |
| `POST` | `/users/create_user` | Public | Register a user. |
| `POST` | `/users/login` | Public | OAuth2 password login; submit form fields `username` (email) and `password`. |
| `GET` | `/users/me` | JWT | Return the current user profile. |
| `PATCH` | `/users/update_user` | JWT | Update the current user profile. |
| `DELETE` | `/users/delete_user` | JWT | Delete the current user. |
| `POST` | `/users/add_skills` | JWT | Add one or more skills to the current user. |
| `DELETE` | `/users/delete_skills` | JWT | Remove one or more skills from the current user. The request body is a list of skill objects. |
| `GET` | `/users/{user_id}` | Public | Current development placeholder returning a dummy username; it is not a user lookup implementation. |

### Internal endpoints

| Method | Path | Access | Description |
| --- | --- | --- | --- |
| `POST` | `/internal/create_skills` | Internal API key | Create an item in the shared skill catalog. |
| `DELETE` | `/internal/delete_skills` | Internal API key | Delete all items from the shared skill catalog. Use only in a trusted administrative context. |

## Authentication and access control

### JWT for user actions

`POST /users/login` expects `application/x-www-form-urlencoded` data because it uses `OAuth2PasswordRequestForm`:

```text
username=user@example.com
password=your-password
```

On successful login, the API returns an access token. Send it to user-protected endpoints:

```http
Authorization: Bearer <access_token>
```

The token stores the authenticated user's identifier in its `sub` claim. Protected personal endpoints use this identifier rather than accepting a user ID from the client.

### Internal API key

The internal router uses a different guard from JWT authentication. Send the value configured as `internal_api_key` in this header:

```http
X-Internal-API-Key: <internal_api_key>
```

This key is intended for trusted backend or administrative operations, not normal end users.

## Data model

The current model consists of three entities:

```text
Person 1 ──── * PersonSkills * ──── 1 Skills
```

- `Person` stores account and profile data, including the password hash.
- `Skills` is the shared catalog of named skills.
- `PersonSkills` is the association entity connecting a user to a skill.

`Person.email` and `Skills.name` are unique in the current schema.

## Roadmap

The full roadmap is maintained in [PLAN.md](PLAN.md). The following capabilities are planned and are **not implemented yet**:

1. Stabilize API contracts, standardized errors, ownership checks, documentation, and broader test coverage.
2. Move from SQLite to PostgreSQL, introduce Alembic migrations, and expand the data model for directions, vacancies, analyses, and roadmaps.
3. Import and normalize JSON/CSV vacancy datasets with deduplication.
4. Extract vacancy requirements through an OpenAI-compatible LLM API with a keyword-based fallback.
5. Calculate market statistics, skill gaps, and prioritized learning roadmaps.
6. Add a Jinja-based web interface.
7. Run imports and analyses in Celery workers with RabbitMQ, Redis, PostgreSQL, and Docker Compose.
8. Extend unit, integration, and demonstration testing.

## Current limitations

- SQLite is the current development database; PostgreSQL and migrations are not implemented.
- No vacancy import, LLM integration, analysis, skill-gap calculation, roadmap, or web UI exists yet.
- The application schema is created with `Base.metadata.create_all()` at startup.
- The internal bulk-delete endpoint removes catalog skills and should be treated as an administrative operation.

## License

No license file is currently included in the repository.
