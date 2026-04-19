from __future__ import annotations

import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    data_path = Path(path)
    with data_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
