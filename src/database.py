"""
database.py — SQLAlchemy models and CRUD helpers for EURON Water Tracker.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.logger import logger

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent / "water_tracker.db"
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class WaterIntake(Base):
    """Stores individual water intake log entries."""

    __tablename__ = "water_intake"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount_ml = Column(Float, nullable=False)
    note = Column(String, nullable=True)
    logged_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    log_date = Column(Date, default=date.today, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "amount_ml": self.amount_ml,
            "note": self.note,
            "logged_at": self.logged_at.isoformat() if self.logged_at else None,
            "log_date": self.log_date.isoformat() if self.log_date else None,
        }


class DailyGoal(Base):
    """Stores per-day hydration goals."""

    __tablename__ = "daily_goal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    goal_date = Column(Date, unique=True, nullable=False, default=date.today)
    goal_ml = Column(Float, nullable=False, default=2000.0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal_date": self.goal_date.isoformat() if self.goal_date else None,
            "goal_ml": self.goal_ml,
        }


# Create tables on import
Base.metadata.create_all(ENGINE)
logger.info(f"Database initialised at {DB_PATH}")


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


def log_intake(amount_ml: float, note: Optional[str] = None) -> WaterIntake:
    """Log a new water intake entry for today."""
    entry = WaterIntake(
        amount_ml=amount_ml,
        note=note,
        logged_at=datetime.utcnow(),
        log_date=date.today(),
    )
    with SessionLocal() as session:
        session.add(entry)
        session.commit()
        session.refresh(entry)
        result = entry.to_dict()
    logger.info(f"Logged {amount_ml} ml — note: {note!r}")
    # Return a plain dict to avoid detached-instance issues
    return result


def get_intake_history(days: int = 7) -> list[dict]:
    """Return intake entries for the last *days* days, newest first."""
    from datetime import timedelta

    cutoff = date.today() - timedelta(days=days - 1)
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(WaterIntake)
                .where(WaterIntake.log_date >= cutoff)
                .order_by(WaterIntake.logged_at.desc())
            )
            .scalars()
            .all()
        )
        return [r.to_dict() for r in rows]


def get_today_total() -> float:
    """Return total ml consumed today."""
    with SessionLocal() as session:
        total = session.execute(
            select(func.sum(WaterIntake.amount_ml)).where(
                WaterIntake.log_date == date.today()
            )
        ).scalar()
    return float(total or 0.0)


def get_daily_goal(for_date: Optional[date] = None) -> float:
    """Return the hydration goal (ml) for a given date. Defaults to today."""
    target = for_date or date.today()
    with SessionLocal() as session:
        row = session.execute(
            select(DailyGoal).where(DailyGoal.goal_date == target)
        ).scalar_one_or_none()
        return float(row.goal_ml) if row else 2000.0


def set_daily_goal(goal_ml: float, for_date: Optional[date] = None) -> DailyGoal:
    """Set or update the hydration goal for a date."""
    target = for_date or date.today()
    with SessionLocal() as session:
        row = session.execute(
            select(DailyGoal).where(DailyGoal.goal_date == target)
        ).scalar_one_or_none()
        if row:
            row.goal_ml = goal_ml
        else:
            row = DailyGoal(goal_date=target, goal_ml=goal_ml)
            session.add(row)
        session.commit()
        result = row.to_dict()
    logger.info(f"Daily goal set to {goal_ml} ml for {target}")
    return result


def delete_intake(entry_id: int) -> bool:
    """Delete a single intake entry by ID. Returns True if deleted."""
    with SessionLocal() as session:
        row = session.get(WaterIntake, entry_id)
        if row is None:
            return False
        session.delete(row)
        session.commit()
    logger.info(f"Deleted intake entry #{entry_id}")
    return True


def get_weekly_summary() -> list[dict]:
    """Return daily totals and goals for the last 7 days."""
    from datetime import timedelta

    today = date.today()
    summary = []
    with SessionLocal() as session:
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            total = session.execute(
                select(func.sum(WaterIntake.amount_ml)).where(
                    WaterIntake.log_date == d
                )
            ).scalar() or 0.0
            goal_row = session.execute(
                select(DailyGoal).where(DailyGoal.goal_date == d)
            ).scalar_one_or_none()
            goal = float(goal_row.goal_ml) if goal_row else 2000.0
            summary.append(
                {
                    "date": d.isoformat(),
                    "day": d.strftime("%a"),
                    "total_ml": float(total),
                    "goal_ml": goal,
                    "pct": round(float(total) / goal * 100, 1) if goal else 0,
                }
            )
    return summary
