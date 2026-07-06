"""
logger.py — Loguru-based logging configuration for EURON Water Tracker.
"""

import sys
from pathlib import Path
from loguru import logger

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Remove default handler
logger.remove()

# Console handler — human-readable, colorized
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> — <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# File handler — full details, rotation daily
logger.add(
    LOG_DIR / "water_tracker_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
    level="DEBUG",
    rotation="00:00",
    retention="7 days",
    compression="zip",
)

__all__ = ["logger"]
