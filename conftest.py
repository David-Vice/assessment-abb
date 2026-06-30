import asyncio
import os
import sys

# psycopg's async driver requires a selector-based event loop; Windows defaults
# to ProactorEventLoop, which raises `InterfaceError` on every connection. This
# must run before pytest-asyncio creates its first event loop, hence the
# root-level conftest (loaded before any test file is collected).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# `.env` points DATABASE_URL/REDIS_URL at the docker-internal hostnames
# (`postgres`, `redis`), which only resolve from inside the compose network.
# Tests run on the host (against the same services via their published ports —
# see docker-compose.yml), so default to localhost unless a real env var
# already overrides it (e.g. in CI). `setdefault` never clobbers an explicit
# environment variable, only the weaker `.env`-file-sourced value pydantic
# would otherwise apply.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://abb:abb@localhost:5432/abb_rag")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
