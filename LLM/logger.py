import json
from pathlib import Path


class ExperimentLogger:
    def __init__(self, path=None):
        self.path = Path(path) if path else None

    def log(self, record):
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=True) + "\n")
