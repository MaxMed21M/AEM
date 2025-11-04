"""Session history utilities."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class HistoryManager:
    """Handle lightweight JSONL session history storage."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def new_session_file(self) -> Path:
        now = datetime.now()
        day_dir = self.base_dir / now.strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        file_path = day_dir / f"session-{int(now.timestamp())}.jsonl"
        file_path.touch(exist_ok=True)
        return file_path

    def append_record(self, file_path: Path, record: Dict[str, Any]) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")

    def list_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        if not self.base_dir.exists():
            return items
        for day_dir in sorted(self.base_dir.iterdir()):
            if not day_dir.is_dir():
                continue
            for file in sorted(day_dir.glob("session-*.jsonl")):
                try:
                    stat = file.stat()
                except FileNotFoundError:
                    continue
                items.append(
                    {
                        "path": file,
                        "label": f"{day_dir.name} — {file.stem.split('-', 1)[-1]}",
                        "updated_at": datetime.fromtimestamp(stat.st_mtime),
                    }
                )
        items.sort(key=lambda item: item["updated_at"], reverse=True)
        return items[:limit]

    def load_last_record(self, file_path: Path) -> Optional[Dict[str, Any]]:
        if not file_path.exists():
            return None
        last_line = ""
        with file_path.open("r", encoding="utf-8") as fp:
            for line in fp:
                if line.strip():
                    last_line = line
        if not last_line:
            return None
        try:
            return json.loads(last_line)
        except json.JSONDecodeError:
            return None
