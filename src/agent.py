"""
agent.py — LangChain-powered AI water intake advisor for EURON Water Tracker.

The agent answers hydration questions, gives personalized advice, and can
read the database to provide context-aware responses.
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from src.logger import logger

# ---------------------------------------------------------------------------
# Conditional LangChain import — graceful fallback when API key is missing
# ---------------------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_AGENT_AVAILABLE = bool(OPENAI_API_KEY)

if _AGENT_AVAILABLE:
    try:
        from langchain.agents import AgentExecutor, create_openai_functions_agent
        from langchain.tools import tool
        from langchain_openai import ChatOpenAI
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain.schema import SystemMessage
        logger.info("LangChain + OpenAI loaded successfully")
    except ImportError as exc:
        logger.warning(f"LangChain import failed: {exc}. AI features disabled.")
        _AGENT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Tools (always defined so they can be reused even without the agent)
# ---------------------------------------------------------------------------


def _get_today_summary_tool() -> str:
    """Fetch today's water intake summary from the database."""
    from src.database import get_today_total, get_daily_goal
    total = get_today_total()
    goal = get_daily_goal()
    remaining = max(0.0, goal - total)
    pct = round(total / goal * 100, 1) if goal else 0
    return (
        f"Today's intake: {total:.0f} ml / {goal:.0f} ml goal "
        f"({pct}% complete). Remaining: {remaining:.0f} ml."
    )


def _get_weekly_summary_tool() -> str:
    """Return a concise weekly hydration summary."""
    from src.database import get_weekly_summary
    rows = get_weekly_summary()
    lines = [f"{r['day']} ({r['date']}): {r['total_ml']:.0f}/{r['goal_ml']:.0f} ml ({r['pct']}%)" for r in rows]
    return "Weekly summary:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# WaterIntakeAgent class
# ---------------------------------------------------------------------------


SYSTEM_PROMPT = """You are EURON — a friendly, knowledgeable AI hydration coach.
Your job is to help users track water intake, understand hydration science,
and build healthy drinking habits.

Guidelines:
- Be encouraging, warm, and motivating.
- Provide evidence-based hydration advice.
- Reference the user's actual data when available using the provided tools.
- Keep responses concise (2–4 sentences max) unless a detailed explanation is requested.
- If you don't have an API key, tell the user politely and offer general advice.
"""


class WaterIntakeAgent:
    """High-level wrapper around the LangChain agent."""

    def __init__(self) -> None:
        self._executor: Optional[object] = None
        self._ready = False

        if not _AGENT_AVAILABLE:
            logger.warning("AI agent disabled: OPENAI_API_KEY not set.")
            return

        try:
            self._build_agent()
            self._ready = True
            logger.info("WaterIntakeAgent initialised successfully")
        except Exception as exc:
            logger.error(f"Failed to build agent: {exc}")

    def _build_agent(self) -> None:
        """Construct the LangChain agent with tools."""

        @tool
        def get_today_summary() -> str:
            """Get today's water intake total and goal."""
            return _get_today_summary_tool()

        @tool
        def get_weekly_summary() -> str:
            """Get the last 7-day water intake summary."""
            return _get_weekly_summary_tool()

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=OPENAI_API_KEY,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        tools = [get_today_summary, get_weekly_summary]
        agent = create_openai_functions_agent(llm, tools, prompt)
        self._executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            max_iterations=5,
            handle_parsing_errors=True,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        return self._ready

    def chat(self, message: str, history: Optional[list] = None) -> str:
        """Send a message and return the agent's response."""
        if not self._ready:
            return self._fallback_response(message)
        try:
            result = self._executor.invoke(
                {
                    "input": message,
                    "chat_history": history or [],
                }
            )
            return result.get("output", "I couldn't generate a response. Please try again.")
        except Exception as exc:
            logger.error(f"Agent error: {exc}")
            return f"Sorry, I encountered an error: {exc}. Please check your API key."

    def _fallback_response(self, message: str) -> str:
        """Provide a helpful response when the AI agent is unavailable."""
        msg_lower = message.lower()
        today_data = _get_today_summary_tool()

        if any(k in msg_lower for k in ["today", "status", "how much", "intake"]):
            return f"📊 {today_data}\n\n*AI coaching is unavailable — add your OPENAI_API_KEY to .env to enable it.*"
        if any(k in msg_lower for k in ["week", "history", "summary"]):
            return f"📅 {_get_weekly_summary_tool()}\n\n*AI coaching is unavailable — add your OPENAI_API_KEY to .env to enable it.*"
        if any(k in msg_lower for k in ["goal", "recommend", "should"]):
            return (
                "💧 General recommendation: Aim for **2,000–3,000 ml** per day for most adults. "
                "Factors like body weight, activity level, and climate may increase this.\n\n"
                "*AI coaching is unavailable — add your OPENAI_API_KEY to .env to enable it.*"
            )
        return (
            "👋 I'm EURON, your hydration coach! I can track your water intake and provide advice. "
            f"\n\n{today_data}\n\n"
            "*AI coaching is unavailable — add your OPENAI_API_KEY to .env to enable it.*"
        )
