import json
from pathlib import Path


def read_jsonl(path: str | Path) -> list[dict]:
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
