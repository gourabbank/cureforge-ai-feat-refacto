# CureForge Agent Guidance

## Setup

- Use `uv` for package management (preferred per instructions)
- Install dependencies: `uv sync`
- Activate environment: `source .venv/bin/activate` (or use `uv run`)

## Running the Application

- Demo: `python app/main.py`
- Docker: `docker compose up` (starts app, redis, litellm services)
- Services depend on: redis and litellm must be healthy

## Testing

- Run tests: `pytest`
- Run with coverage: `pytest --cov=app`
- Test dependencies include: pytest, pytest-asyncio, pytest-cov, pytest-mock, fakeredis

## Linting

- Run ruff: `ruff check .`
- Fix issues: `ruff check --fix .`

## Important Conventions

- Always check `references/` for relevant information before acting
- When instructed to "future document", work in `docs/future/` (markdown only)
- When instructed to "create tasks", work in `docs/outsource_tasks/` (markdown only)
- No emojis or em dashes in code/comments
- Keep inline comments rare and to the point
- Use correct Python venv (prefer `uv`)
- When something isn't clear or ambiguous, ask for clarification. Don't make assumptions.
- When creating tasks, include a general "big picture" description of the project as a whole.

## Project Structure

- Main entrypoint: `app/main.py`
- Core logic: `app/src/` (agent, phases, tools, middlewares)
- Prompts: `app/prompts/`
- Tests: `app/tests/`
- Configuration: `.env` (example: `.env.example`)
