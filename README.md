# FastAPI Monolith Template

Template for building medium-sized monoliths powered by FastAPI and modern
Python (3.14).

## Features

- ⚡ Backend development with `FastAPI`
- 📦 Blazing-fast dependency management with `uv`
- 🧹 Linting + formatting with `ruff`
- 🧠 Static type checking with `mypy`
- 🧪 Testing + coverage with `pytest` and `asyncio`
- 🐳 Dockerized environment for reproducible dev & CI
- 🗃 `PostgreSQL` + `SQLAlchemy 2.0`
- 🔁 `Alembic` migrations
- 🔐 Service-to-service authentication ready
- 🧰 `Makefile` for common tasks
- 🔒 Optional `pre-commit` hooks

## Project Structure

The project follows a **Vertical Slice Architecture**. Instead of traditional
layering (controllers, services, repositories) that splits functionality across
the entire project, each directory within `backend/app/` represents a specific
domain feature (a "slice") and contains everything it needs to function.

```text
.
├── backend/
│   ├── app/                       # Main application code
│   │   ├── auth/                  # Auth slice
│   │   │   ├── router.py
│   │   │   └── schemas.py
│   │   ├── core/                  # Configuration, security, utils
│   │   │   ├── config.py
│   │   │   ├── consts.py
│   │   │   ├── database.py
│   │   │   ├── deps.py
│   │   │   ├── logging_config.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── security.py
│   │   │   └── utils.py
│   │   ├── health/                # Health slice
│   │   │   └── router.py
│   │   ├── items/                 # Items slice
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── users/                 # Users slice
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   └── main.py
│   ├── docker/                    # Docker files
│   ├── migrations/                # Alembic migrations
│   ├── scripts/                   # Startup and initialization scripts
│   └── tests/                     # Pytest suite
├── docker-compose.yaml
├── docker-compose.test.yaml
├── Makefile
└── pyproject.toml
```

## Goals

The main goal of this template is to provide a clean, modular, and scalable
foundation for building medium-sized monoliths with FastAPI. 

While microservices are popular, they often introduce premature complexity
(distributed systems, network latency, operational overhead) that many projects
don't need initially.

This template promotes a **Modular Monolith** approach using **Vertical Slices**,
ensuring that the codebase remains organized and features are decoupled. This
makes it significantly easier to transition specific modules into independent
microservices later if the need arises.

### Intentionally not included

To keep the template focused and lightweight, the following are not included:

- Frontend
- Redis / caching
- Celery / background jobs
- Identity providers (Auth0, Keycloak, etc.) / social auth
- Deployment pipelines

### Authentication

This template implements **JWT-based authentication** using FastAPI's
`OAuth2PasswordBearer`.

- **Token Generation**: Users can obtain an access token by providing their
email and password at the `/api/v1/auth/token` endpoint.

- **Password Hashing**: Secure password storage is handled by `pwdlib` using
recommended hashing algorithms.

- **Protection**: Routes can be protected by injecting the current user
dependency, which validates the JWT and user permissions.

## Local Development

### Prerequisites

Install:
- [uv](https://docs.astral.sh/uv/)
- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)

### Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/brunosilvagrego/fastapi-template-vertical-slices.git
   cd fastapi-template-vertical-slices
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Environment Configuration**:
   The template uses `.env.dev` for development by default. You can modify it
   if needed.

4. **Run the application**:
   The application automatically runs migrations on startup.

   ```bash
   make up
   ```

   The API will be available at [http://localhost:8000](http://localhost:8000).
   You can access the interactive documentation at
   [http://localhost:8000/docs](http://localhost:8000/docs).

### Common Tasks

The project uses a `Makefile` to simplify common development tasks:

| Command | Description |
|---------|-------------|
| `make up` | Start the API and Database |
| `make down` | Stop all containers |
| `make down ARGS=-v` | Stop all containers and delete database |
| `make format` | Run ruff format |
| `make lint-fix` | Run ruff check and fix issues |
| `make check-types` | Run mypy type checking |
| `make code-cleanup` | Run format, lint-fix and check-types at once |
| `make requirements-all` | Export production and development requirements to corresponding files |
| `make precommit-install` | Install pre-commit hooks for automatic code cleanup |
| `make alembic-new MSG="..."` | Create a new database migration |
| `make alembic-upgrade` | Apply database migrations |
| `make test` | Run tests with coverage inside a container |
| `make test-with-cleanup` | Run tests and cleanup docker resources |
| `make help` | Show all available commands |

### Handling Dependencies

Add new packages with boundaries:

```bash
uv add --bounds major fastapi
uv add --dev --bounds major pytest ruff
```

Update requirements files:

```bash
make requirements-all
```

## References

This template was based on the microservices template:

- [brunosilvagrego/fastapi-template-microservices](https://github.com/brunosilvagrego/fastapi-template-microservices)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE)
file for details.
