"""
api.py — FastAPI REST endpoints for EURON Water Tracker.

Run with:  uvicorn src.api:app --reload
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.database import (
    delete_intake,
    get_daily_goal,
    get_intake_history,
    get_today_total,
    get_weekly_summary,
    log_intake,
    set_daily_goal,
)
from src.logger import logger

app = FastAPI(
    title="EURON Water Tracker API",
    description="REST API for logging and querying daily water intake.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class IntakeCreate(BaseModel):
    amount_ml: float = Field(..., gt=0, description="Amount of water in millilitres")
    note: Optional[str] = Field(None, description="Optional note (e.g. 'post-workout')")


class GoalSet(BaseModel):
    goal_ml: float = Field(..., gt=0, description="Daily hydration goal in millilitres")
    goal_date: Optional[date] = Field(None, description="Date for the goal (default: today)")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "EURON Water Tracker"}


@app.get("/today", tags=["intake"])
def today_status():
    """Return today's total intake and goal."""
    total = get_today_total()
    goal = get_daily_goal()
    return {
        "date": date.today().isoformat(),
        "total_ml": total,
        "goal_ml": goal,
        "remaining_ml": max(0.0, goal - total),
        "percent_complete": round(total / goal * 100, 1) if goal else 0,
    }


@app.post("/intake", tags=["intake"], status_code=201)
def add_intake(body: IntakeCreate):
    """Log a water intake entry."""
    entry = log_intake(amount_ml=body.amount_ml, note=body.note)
    logger.info(f"POST /intake — {body.amount_ml} ml")
    return {"message": "Logged successfully", "entry": entry}


@app.get("/history", tags=["intake"])
def history(days: int = 7):
    """Return intake history for the last N days."""
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="days must be between 1 and 90")
    return {"days": days, "entries": get_intake_history(days=days)}


@app.delete("/intake/{entry_id}", tags=["intake"])
def remove_intake(entry_id: int):
    """Delete a specific intake log entry."""
    success = delete_intake(entry_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Entry #{entry_id} not found")
    return {"message": f"Entry #{entry_id} deleted"}


@app.get("/goal", tags=["goal"])
def get_goal(goal_date: Optional[date] = None):
    """Get the hydration goal for a date."""
    goal = get_daily_goal(for_date=goal_date)
    return {"date": (goal_date or date.today()).isoformat(), "goal_ml": goal}


@app.post("/goal", tags=["goal"])
def update_goal(body: GoalSet):
    """Set or update the daily hydration goal."""
    result = set_daily_goal(goal_ml=body.goal_ml, for_date=body.goal_date)
    return {"message": "Goal updated", "goal": result}


@app.get("/summary/weekly", tags=["summary"])
def weekly_summary():
    """Return a 7-day daily summary of intake vs. goal."""
    return {"summary": get_weekly_summary()}
