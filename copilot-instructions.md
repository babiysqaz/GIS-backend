# Copilot instructions for GIS-backend

Purpose
- Provide precise, actionable rules for Copilot-style code generation and edits within the backend repository.

Scope
- Backend only: files under `gis-backend/` in this workspace.
- Do not modify `gis-frontend/` unless explicitly asked.

High-level goals
- Keep the API aligned with `/api/v1` semantics and existing layer/user contract.
- Preserve FastAPI async patterns, SQLAlchemy 2.0 typed models, and Pydantic v2 schema design.
- Maintain separation between router, service, and model layers.

Project conventions
- Python version: `3.11+`.
- Use `snake_case` for files, functions, variables, and module names.
- Use `PascalCase` for classes, Pydantic schemas, and Enum members.
- Constants must use `UPPER_SNAKE_CASE`.
- Use `pydantic-settings` for configuration and environment variables.

Folder responsibilities
- `app/main.py`: FastAPI app creation, router registration, CORS settings.
- `app/config.py`: app settings and environment configuration.
- `app/database.py`: async SQLAlchemy engine, session factory, and `Base` declaration.
- `app/dependencies.py`: shared dependency providers like `get_db`, `get_current_user`, `require_admin`.
- `app/models/`: SQLAlchemy models only.
- `app/schemas/`: Pydantic request/response schemas.
- `app/routers/`: API routers with dependency injection only.
- `app/services/`: business logic and database operations.
- `tests/`: pytest test cases for auth and layer features.

API and router rules
- API prefix is `/api/v1`; keep new endpoints consistent with versioning.
- Use `APIRouter(prefix="/layers", tags=["layers"])` for layer endpoints.
- Router functions must not contain raw DB queries; delegate to service layer.
- Use `Depends(get_current_user)` for authenticated read routes.
- Use `Depends(require_admin)` for admin-only mutation routes.
- Use `response_model` on routes to enforce output schema.
- Use `status_code=status.HTTP_201_CREATED` for successful create operations.

SQLAlchemy model rules
- Use `DeclarativeBase`, `Mapped`, and `mapped_column` from SQLAlchemy 2.0.
- Annotate all mapped fields with `Mapped[...]` and use typed columns.
- Use explicit defaults for optional fields.
- Use UTC-aware timestamps via `datetime.datetime.utcnow` for `created_at` / `updated_at`.

Pydantic schema rules
- Use separate schema classes for input and output.
- `LayerCreate` should inherit from `LayerBase` and represent create payload.
- `LayerUpdate` should define all fields as optional (`| None`) for PATCH semantics.
- `LayerResponse` should include `id`, `created_at`, `updated_at`, and set `model_config = {"from_attributes": True}` for ORM compatibility.
- Avoid `any`; use concrete types and `Literal` when values are constrained.

Authentication rules
- JWT is handled by `python-jose` and password hashing by `passlib` with bcrypt.
- `auth.py` router should expose `POST /auth/login` and `/auth/refresh`.
- Use secure token expiration and proper exception handling for invalid credentials.

Testing rules
- Use `pytest` with `pytest-asyncio` and `httpx.AsyncClient`.
- Add tests for important API behaviors, authentication flows, and layer CRUD operations.
- Keep test fixtures in `tests/conftest.py` and isolate DB state between tests.

Stylistic rules
- Use `async def` for all route handlers and service operations.
- Keep business logic in services and validation in schemas.
- Keep functions small and focused; prefer helper functions over large route bodies.
- Use explicit imports and avoid wildcard imports.

Forbidden actions
- Do not add raw SQL queries inside router functions.
- Do not bypass service layer or directly mutate SQLAlchemy models from routers.
- Do not add ArcGIS or frontend-specific code in the backend.
- Do not change the API prefix or versioning without clear user guidance.

When uncertain
- Ask the user for clarification on API contract, response shape, or authorization rules.
- If a change affects persistence or authentication, keep it minimal and add tests.

Generated: follow these rules when making automated edits or suggestions in `gis-backend/`.
