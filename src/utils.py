"""
utils.py
========
Helper functions jo poore project mein use hoti hain.
"""

import os
import glob
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def ensure_dirs(*dirs: str) -> None:
    """
    Multiple directories create karta hai agar exist nahi karte.

    Args:
        *dirs: Directory paths to create.
    """
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        logger.debug("Directory ensured: %s", d)


def format_duration(seconds: float) -> str:
    """
    Seconds ko human-readable format mein convert karta hai.

    Examples:
        90   → "1 min 30 sec"
        3661 → "1 hr 1 min 1 sec"

    Args:
        seconds: Duration in seconds.

    Returns:
        Human-readable duration string.
    """
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(f"{hours} hr")
    if minutes:
        parts.append(f"{minutes} min")
    if secs or not parts:
        parts.append(f"{secs} sec")

    return " ".join(parts)


def clean_temp_files(directory: str, pattern: str = "*_extracted.wav") -> int:
    """
    Temporary extracted audio files clean karta hai.

    Args:
        directory: Directory to clean.
        pattern: Glob pattern for files to delete.

    Returns:
        Number of files deleted.
    """
    count = 0
    search_path = str(Path(directory) / pattern)
    for filepath in glob.glob(search_path):
        try:
            os.remove(filepath)
            logger.debug("Deleted temp file: %s", filepath)
            count += 1
        except OSError as exc:
            logger.warning("File delete nahi hua: %s - %s", filepath, exc)
    return count


def get_file_size_mb(file_path: str) -> float:
    """
    File size MB mein return karta hai.

    Args:
        file_path: Path to the file.

    Returns:
        File size in megabytes.
    """
    try:
        return Path(file_path).stat().st_size / (1024 * 1024)
    except OSError:
        return 0.0


def setup_logging(level: str = "INFO") -> None:
    """
    Application-wide logging configure karta hai.

    Args:
        level: Log level string - DEBUG, INFO, WARNING, ERROR.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_file(file_path: str, supported_formats: set) -> None:
    """
    File existence aur format validate karta hai.

    Args:
        file_path: Path to validate.
        supported_formats: Set of allowed extensions (e.g. {'.mp4', '.wav'}).

    Raises:
        FileNotFoundError: Agar file exist nahi karta.
        ValueError: Agar format supported nahi hai.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File nahi mili: {file_path}")
    if path.suffix.lower() not in supported_formats:
        raise ValueError(
            f"Format '{path.suffix}' supported nahi hai.\n"
            f"Supported formats: {sorted(supported_formats)}"
        )


def list_output_files(output_dir: str = "outputs") -> List[dict]:
    """
    Output directory mein saari generated files list karta hai.

    Args:
        output_dir: Directory to scan.

    Returns:
        List of dicts: [{name, path, size_mb, created}]
    """
    files = []
    output_path = Path(output_dir)
    if not output_path.exists():
        return files

    for f in sorted(output_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix.lower() in {".pdf", ".docx", ".md"} and f.is_file():
            stat = f.stat()
            files.append({
                "name": f.name,
                "path": str(f),
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    return files


def truncate_text(text: str, max_chars: int = 500, suffix: str = "...") -> str:
    """
    Long text ko preview ke liye truncate karta hai.

    Args:
        text: Input text.
        max_chars: Maximum characters to keep.
        suffix: Suffix to add when truncated.

    Returns:
        Truncated text string.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + suffix
