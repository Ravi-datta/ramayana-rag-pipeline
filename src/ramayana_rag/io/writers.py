import json
from pathlib import Path
from typing import Iterable


def ensure_parent_dir(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def write_jsonl(records: Iterable[dict], output_path: str | Path) -> None:
    output_path = Path(output_path)
    ensure_parent_dir(output_path)

    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
