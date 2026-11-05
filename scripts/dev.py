#!/usr/bin/env python3
"""One entry point for local work on the booking core. Runs on Windows, macOS and Linux
with plain Python 3.10+ and Docker; no make, no shell tricks.

    python scripts/dev.py up            # build and start postgres, migrate, api :8000, worker
    python scripts/dev.py docs          # open http://localhost:8000/api/docs (Swagger, ReDoc, docs)
    python scripts/dev.py seed          # demo tenant: 2 sites, 3 resource types, rules, people
    python scripts/dev.py token <sub>   # a 12-hour dev JWT for any person
    python scripts/dev.py timers <tenantId>   # make that tenant's pending timers due now
    python scripts/dev.py logs [api|worker|postgres]
    python scripts/dev.py psql          # SQL shell as the app role (RLS applies)
    python scripts/dev.py check         # what CI runs: ruff, import contracts, pytest
    python scripts/dev.py down          # stop (data kept)
    python scripts/dev.py reset         # stop and DELETE the local database, then up

Run from the repository root (the folder with infra/ and core/).
"""

import os
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_URL = "http://localhost:8000/api/docs"
# Team notes in a docs/ folder next to the repository are shown at /api/docs too.
if (ROOT.parent / "docs").is_dir():
    os.environ.setdefault("WORKSPACE_DOCS_DIR", str(ROOT.parent / "docs"))
API_DIR = ROOT / "core" / "api"
COMPOSE = ["docker", "compose", "-f", str(ROOT / "infra" / "compose.yaml")]
# Management commands inside the api container run with local settings: DEBUG on, so dev
# tokens can be minted. The server itself keeps running with production settings.
EXEC_LOCAL = [
    *COMPOSE,
    "exec",
    "-T",
    "-e",
    "DJANGO_SETTINGS_MODULE=app.settings.local",
    "-e",
    "PYTHONIOENCODING=utf-8",
    "api",
    "python",
    "manage.py",
]


def run(cmd: list[str], **kw: object) -> int:
    print("$", " ".join(cmd), flush=True)
    return subprocess.call(cmd, **kw)  # type: ignore[arg-type]


def wait_healthy(url: str = "http://localhost:8000/api/healthz", seconds: int = 90) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    print("API is up:", url)
                    return
        except OSError:
            time.sleep(1)
    sys.exit("API did not come up; see: python scripts/dev.py logs api")


def venv_python() -> str:
    for candidate in (
        API_DIR / ".venv" / "Scripts" / "python.exe",
        API_DIR / ".venv" / "bin" / "python",
    ):
        if candidate.exists():
            return str(candidate)
    sys.exit(
        "No virtualenv in core/api/.venv. Create it once:\n"
        "  cd core/api && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt"
    )


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if shutil.which("docker") is None and argv[0] != "check":
        sys.exit("Docker is not on PATH. Start Docker Desktop first.")
    cmd, args = argv[0], argv[1:]
    if cmd == "up":
        code = run([*COMPOSE, "up", "-d", "--build"])
        if code == 0:
            wait_healthy()
            print("Docs:", DOCS_URL)
        return code
    if cmd == "docs":
        import webbrowser

        print(DOCS_URL)
        webbrowser.open(DOCS_URL)
        return 0
    if cmd == "down":
        return run([*COMPOSE, "down"])
    if cmd == "reset":
        run([*COMPOSE, "down", "-v"])
        return main(["up"])
    if cmd == "seed":
        return run([*EXEC_LOCAL, "seed_demo", *args])
    if cmd == "token":
        if not args:
            sys.exit("Usage: python scripts/dev.py token <sub> [--email someone@x.test]")
        return run([*EXEC_LOCAL, "dev_token", "--sub", args[0], *args[1:]])
    if cmd == "manage":
        return run([*EXEC_LOCAL, *args])
    if cmd == "timers":
        if not args:
            sys.exit("Usage: python scripts/dev.py timers <tenantId>")
        try:
            tenant = uuid.UUID(args[0])
        except ValueError:
            sys.exit("tenantId must be a UUID.")
        sql = (
            "UPDATE scheduled_jobs SET run_at = now() "
            f"WHERE status = 'PENDING' AND tenant_id = '{tenant}' "
            "RETURNING job_type, record_id;"
        )
        return run(
            [
                *COMPOSE,
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "postgres",
                "-d",
                "booking_core",
                "-c",
                sql,
            ]
        )
    if cmd == "psql":
        return run(
            [*COMPOSE, "exec", "postgres", "psql", "-U", "booking_app", "-d", "booking_core"],
            env={**os.environ, "PGPASSWORD": "booking_app"},
        )
    if cmd == "logs":
        return run([*COMPOSE, "logs", "-f", "--tail", "100", *args])
    if cmd == "check":
        py = venv_python()
        env = {**os.environ, "DJANGO_SETTINGS_MODULE": "app.settings.test"}
        for step in (
            [py, "-m", "ruff", "check", "."],
            [py, "-m", "ruff", "format", "--check", "."],
            [str(Path(py).with_name("lint-imports" + (".exe" if os.name == "nt" else "")))],
            [py, "-m", "pytest", "tests", "-q", *args],
        ):
            if run(step, cwd=API_DIR, env=env) != 0:
                return 1
        return 0
    sys.exit(f"Unknown command {cmd!r}. Try: python scripts/dev.py help")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
