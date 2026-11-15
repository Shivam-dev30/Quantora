"""Atomic and concurrency-safe YAML persistence helper."""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict
import yaml
from backend.app.core.logging import get_logger

logger = get_logger("atomic_yaml")
_yaml_lock = asyncio.Lock()


async def atomic_write_yaml(path: Path | str, data: Dict[str, Any]) -> bool:
    """
    Atomically writes YAML data to disk under an async lock using a temporary file.
    Guarantees that files are never corrupted, truncated, or half-written during crashes.
    """
    target_path = Path(path).resolve()
    temp_path = target_path.with_suffix(f".tmp.{os.getpid()}")

    async with _yaml_lock:
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, sort_keys=False)
                f.flush()
                os.fsync(f.fileno())

            # Atomic swap
            os.replace(temp_path, target_path)
            return True
        except Exception as e:
            logger.error(f"Failed atomic write to {target_path}: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise


def read_yaml(path: Path | str) -> Dict[str, Any]:
    """Safely read and parse a YAML file, returning an empty dict on missing file."""
    target_path = Path(path).resolve()
    if not target_path.exists():
        return {}
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error reading YAML from {target_path}: {e}")
        return {}
