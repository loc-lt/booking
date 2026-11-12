"""Settings package. Before any settings module runs, the values of `core/api/.env` (when the
file exists) are put into the process environment. Variables already set in the environment
win, so a shell export or a Compose `environment:` entry always overrides the file.

Copy `.env.example` to `.env` to start (`python scripts/dev.py up` does it for you). The file
is read with the standard library: KEY=VALUE per line, `#` comments, optional quotes, no
variable interpolation.
"""

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def load_dotenv(path: Path = ENV_FILE) -> int:
    """Put the file's KEY=VALUE pairs into os.environ unless already set. Returns how many."""
    if not path.is_file():
        return 0
    loaded = 0
    for raw in path.read_text("utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
            loaded += 1
    return loaded


load_dotenv()
