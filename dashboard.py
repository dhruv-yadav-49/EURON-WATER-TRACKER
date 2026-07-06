"""
dashboard.py — EURON Water Tracker · Streamlit Dashboard
Run:  streamlit run dashboard.py
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta

# ── Make sure `src` is importable when running from the project root ──
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd

from src.database import (
    log_intake,
    get_intake_history,
    get_today_total,
    get_daily_goal,
    set_daily_goal,
    get_weekly_summary,
    delete_intake,
)
from src.agent import WaterIntakeAgent

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="EURON Water Tracker",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Dark theme base ── */
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #0d1526 50%, #0a1020 100%);
        color: #e2e8f0;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1a2d 0%, #0a1220 100%);
        border-right: 1px solid rgba(59,130,246,0.15);
    }
    section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

    /* ── Metric cards ── */
    .metric-card {
        background: linear-gradient(135deg, rgba(15,25,50,0.9), rgba(20,35,70,0.7));
        border: 1px solid rgba(59,130,246,0.25);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 12px;
        backdrop-filter: blur(12px);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(59,130,246,0.2);
    }
    .metric-label {
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        color: #64748b;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #3b82f6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
    }
    .metric-sub {
        font-size: 0.82rem;
        color: #64748b;
        margin-top: 4px;
    }

    /* ── Progress ring container ── */
    .ring-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 8px 0;
    }

    /* ── Wave progress bar ── */
    .progress-bar-bg {
        background: rgba(255,255,255,0.06);
        border-radius: 50px;
        height: 12px;
        overflow: hidden;
        margin: 10px 0;
    }
    .progress-bar-fill {
        height: 100%;
        border-radius: 50px;
        background: linear-gradient(90deg, #3b82f6, #06b6d4, #10b981);
        transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* ── Quick-add buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(6,182,212,0.1));
        border: 1px solid rgba(59,130,246,0.3);
        color: #93c5fd !important;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.9rem;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease;
        width: 100%;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(59,130,246,0.3), rgba(6,182,212,0.2));
        border-color: rgba(59,130,246,0.6);
        box-shadow: 0 4px 20px rgba(59,130,246,0.25);
        transform: translateY(-1px);
    }
    .stButton > button:active {
        transform: translateY(0px);
    }

    /* ── Section headers ── */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #e2e8f0;
        margin: 20px 0 12px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* ── Chat bubbles ── */
    .chat-user {
        background: linear-gradient(135deg, rgba(59,130,246,0.25), rgba(37,99,235,0.15));
        border: 1px solid rgba(59,130,246,0.3);
        border-radius: 16px 16px 4px 16px;
        padding: 12px 16px;
        margin: 8px 0;
        max-width: 85%;
        margin-left: auto;
        color: #bfdbfe;
        font-size: 0.9rem;
    }
    .chat-ai {
        background: linear-gradient(135deg, rgba(16,185,129,0.12), rgba(5,150,105,0.08));
        border: 1px solid rgba(16,185,129,0.2);
        border-radius: 16px 16px 16px 4px;
        padding: 12px 16px;
        margin: 8px 0;
        max-width: 85%;
        color: #a7f3d0;
        font-size: 0.9rem;
    }

    /* ── Data table ── */
    .stDataFrame {
        background: rgba(15,25,50,0.6) !important;
        border-radius: 12px;
        overflow: hidden;
    }

    /* ── Input fields ── */
    .stNumberInput input, .stTextInput input, .stSelectbox select {
        background: rgba(15,25,50,0.8) !important;
        border: 1px solid rgba(59,130,246,0.25) !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15,25,50,0.5);
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        color: #64748b;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6, #06b6d4) !important;
        color: white !important;
    }

    /* ── Hero banner ── */
    .hero-banner {
        background: linear-gradient(135deg, rgba(59,130,246,0.15) 0%, rgba(6,182,212,0.1) 50%, rgba(16,185,129,0.08) 100%);
        border: 1px solid rgba(59,130,246,0.2);
        border-radius: 20px;
        padding: 28px 32px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }
    .hero-banner::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(59,130,246,0.1) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #60a5fa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        line-height: 1.2;
    }
    .hero-subtitle {
        color: #64748b;
        font-size: 0.95rem;
        margin-top: 6px;
        font-weight: 400;
    }

    /* ── Toast / success message ── */
    .stSuccess, .stInfo, .stWarning, .stError {
        border-radius: 12px !important;
    }

    /* ── Log entry row ── */
    .log-entry {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(15,25,50,0.5);
        border: 1px solid rgba(59,130,246,0.12);
        border-radius: 10px;
        padding: 10px 16px;
        margin: 6px 0;
        transition: background 0.2s;
    }
    .log-entry:hover { background: rgba(59,130,246,0.08); }
    .log-ml { font-weight: 700; color: #60a5fa; font-size: 1rem; }
    .log-time { color: #64748b; font-size: 0.8rem; }
    .log-note { color: #94a3b8; font-size: 0.82rem; font-style: italic; }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: rgba(15,25,50,0.3); }
    ::-webkit-scrollbar-thumb { background: rgba(59,130,246,0.4); border-radius: 3px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────
if "tracker_started" not in st.session_state:
    st.session_state.tracker_started = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "agent" not in st.session_state:
    st.session_state.agent = WaterIntakeAgent()
if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💧 EURON")
    st.markdown("*Your AI Hydration Coach*")
    st.divider()

    # Daily goal setting
    st.markdown("### 🎯 Daily Goal")
    current_goal = get_daily_goal()
    new_goal = st.number_input(
        "Goal (ml)",
        min_value=500,
        max_value=6000,
        value=int(current_goal),
        step=100,
        key="goal_input",
    )
    if st.button("Update Goal", key="btn_set_goal"):
        set_daily_goal(float(new_goal))
        st.success(f"Goal set to {new_goal} ml!")
        st.rerun()

    st.divider()

    # AI agent status
    agent = st.session_state.agent  # WaterIntakeAgent
    if agent.is_ready:
        st.markdown("🤖 **AI Coach:** ✅ Active")
    else:
        st.markdown("🤖 **AI Coach:** ⚠️ Offline")
        st.caption("Add OPENAI_API_KEY to .env to enable AI coaching.")

    st.divider()

    # Quick stats
    total = get_today_total()
    goal = get_daily_goal()
    pct = min(100.0, total / goal * 100) if goal else 0.0
    st.markdown("### 📊 Today at a Glance")
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Consumed</div>
            <div class="metric-value">{total:.0f} ml</div>
            <div class="metric-sub">of {goal:.0f} ml goal</div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width:{pct:.1f}%"></div>
            </div>
            <div class="metric-sub">{pct:.1f}% complete</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.caption(f"🕐 Last updated: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Refresh", key="btn_refresh"):
        st.rerun()


# ─────────────────────────────────────────────
# Main content
# ─────────────────────────────────────────────

# Hero banner
st.markdown(
    f"""
    <div class="hero-banner">
        <p class="hero-title">💧 EURON Water Tracker</p>
        <p class="hero-subtitle">
            {datetime.now().strftime('%A, %d %B %Y')} &nbsp;·&nbsp;
            Stay hydrated, stay healthy.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Top KPI row
total = get_today_total()
goal = get_daily_goal()
remaining = max(0.0, goal - total)
pct = min(100.0, total / goal * 100) if goal else 0.0
weekly = get_weekly_summary()
streak = sum(1 for d in reversed(weekly) if d["pct"] >= 100)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        f"""<div class="metric-card">
            <div class="metric-label">💧 Today's Intake</div>
            <div class="metric-value">{total:.0f}</div>
            <div class="metric-sub">millilitres consumed</div>
        </div>""",
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"""<div class="metric-card">
            <div class="metric-label">🎯 Remaining</div>
            <div class="metric-value">{remaining:.0f}</div>
            <div class="metric-sub">ml to reach goal</div>
        </div>""",
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f"""<div class="metric-card">
            <div class="metric-label">📈 Progress</div>
            <div class="metric-value">{pct:.0f}%</div>
            <div class="metric-sub">of daily goal</div>
        </div>""",
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        f"""<div class="metric-card">
            <div class="metric-label">🔥 Goal Streak</div>
            <div class="metric-value">{streak}</div>
            <div class="metric-sub">consecutive days</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ─── Tabs ───
tab_log, tab_history, tab_analytics, tab_chat = st.tabs(
    ["➕  Log Intake", "📋  History", "📊  Analytics", "🤖  AI Coach"]
)

# ════════════════════════════════════════════
# Tab 1 — Log Intake
# ════════════════════════════════════════════
with tab_log:
    st.markdown("### Quick Add")
    quick_amounts = [150, 200, 250, 300, 350, 500]
    cols = st.columns(len(quick_amounts))
    for col, amt in zip(cols, quick_amounts):
        with col:
            if st.button(f"💧 {amt} ml", key=f"quick_{amt}"):
                log_intake(amount_ml=float(amt), note="Quick add")
                st.toast(f"✅ Logged {amt} ml!", icon="💧")
                st.rerun()

    st.divider()

    st.markdown("### Custom Amount")
    with st.form("custom_log_form", clear_on_submit=True):
        c1, c2 = st.columns([2, 3])
        with c1:
            custom_ml = st.number_input(
                "Amount (ml)", min_value=1, max_value=3000, value=250, step=10
            )
        with c2:
            custom_note = st.text_input("Note (optional)", placeholder="e.g. Post-workout, Morning glass…")
        submitted = st.form_submit_button("➕ Log Water", use_container_width=True)
        if submitted:
            log_intake(amount_ml=float(custom_ml), note=custom_note or None)
            st.success(f"✅ Logged **{custom_ml} ml** successfully!")
            st.rerun()

    # Today's entries
    st.divider()
    st.markdown("### Today's Entries")
    today_entries = [
        e for e in get_intake_history(days=1)
        if e.get("log_date") == date.today().isoformat()
    ]
    if not today_entries:
        st.info("No entries yet today. Start logging your water intake! 💧")
    else:
        for entry in today_entries:
            logged_at = entry.get("logged_at", "")
            try:
                t = datetime.fromisoformat(logged_at).strftime("%H:%M")
            except Exception:
                t = logged_at[:16]
            note_html = f'<span class="log-note">— {entry["note"]}</span>' if entry.get("note") else ""
            del_col, content_col = st.columns([1, 10])
            with content_col:
                st.markdown(
                    f"""<div class="log-entry">
                        <div>
                            <span class="log-ml">{entry['amount_ml']:.0f} ml</span>
                            &nbsp;{note_html}
                        </div>
                        <span class="log-time">{t}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with del_col:
                if st.button("🗑", key=f"del_{entry['id']}", help="Delete this entry"):
                    delete_intake(entry["id"])
                    st.rerun()


# ════════════════════════════════════════════
# Tab 2 — History
# ════════════════════════════════════════════
with tab_history:
    days_back = st.slider("Show last N days", min_value=1, max_value=30, value=7, key="history_days")
    history = get_intake_history(days=days_back)

    if not history:
        st.info("No history found for the selected period.")
    else:
        df = pd.DataFrame(history)
        df["logged_at"] = pd.to_datetime(df["logged_at"]).dt.strftime("%Y-%m-%d %H:%M")
        df["amount_ml"] = df["amount_ml"].apply(lambda x: f"{x:.0f} ml")
        df = df.rename(columns={
            "id": "ID",
            "amount_ml": "Amount",
            "note": "Note",
            "logged_at": "Logged At",
            "log_date": "Date",
        })
        df = df[["ID", "Date", "Logged At", "Amount", "Note"]]
        st.dataframe(df, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════
# Tab 3 — Analytics
# ════════════════════════════════════════════
with tab_analytics:
    weekly = get_weekly_summary()
    df_w = pd.DataFrame(weekly)

    if df_w.empty:
        st.info("Not enough data yet. Start logging to see analytics!")
    else:
        # Bar chart — intake vs goal
        st.markdown("### 📊 7-Day Intake vs Goal")
        chart_df = df_w.set_index("day")[["total_ml", "goal_ml"]].rename(
            columns={"total_ml": "Intake (ml)", "goal_ml": "Goal (ml)"}
        )
        st.bar_chart(chart_df, use_container_width=True, height=300)

        st.divider()

        # Progress per day
        st.markdown("### ✅ Daily Goal Achievement")
        for _, row in df_w.iterrows():
            bar_pct = min(100.0, row["pct"])
            colour = "#10b981" if row["pct"] >= 100 else "#3b82f6" if row["pct"] >= 60 else "#f59e0b"
            icon = "✅" if row["pct"] >= 100 else "💧"
            st.markdown(
                f"""
                <div style="margin:6px 0;">
                    <div style="display:flex;justify-content:space-between;font-size:0.85rem;color:#94a3b8;margin-bottom:4px;">
                        <span>{icon} {row['day']} <span style="color:#64748b;font-size:0.75rem;">({row['date']})</span></span>
                        <span style="font-weight:600;color:#e2e8f0;">{row['total_ml']:.0f} / {row['goal_ml']:.0f} ml &nbsp;<span style="color:{colour};">{row['pct']:.0f}%</span></span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width:{bar_pct}%;background:linear-gradient(90deg,{colour},{colour}aa);"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.divider()

        # Summary stats
        st.markdown("### 📈 Weekly Stats")
        s1, s2, s3 = st.columns(3)
        avg_intake = df_w["total_ml"].mean()
        days_goal_met = int((df_w["pct"] >= 100).sum())
        best_day_row = df_w.loc[df_w["total_ml"].idxmax()]

        s1.metric("Avg Daily Intake", f"{avg_intake:.0f} ml")
        s2.metric("Days Goal Met", f"{days_goal_met} / 7")
        s3.metric("Best Day", f"{best_day_row['day']} ({best_day_row['total_ml']:.0f} ml)")


# ════════════════════════════════════════════
# Tab 4 — AI Coach Chat
# ════════════════════════════════════════════
with tab_chat:
    agent = st.session_state.agent  # WaterIntakeAgent

    st.markdown("### 🤖 Chat with EURON")
    if not agent.is_ready:
        st.warning(
            "⚠️ AI coaching is in **offline mode**. "
            "Add your `OPENAI_API_KEY` to the `.env` file and restart the app for full AI features.",
            icon="🔑",
        )
    else:
        st.success("✅ Connected to GPT-4o-mini AI coach", icon="🤖")

    # Chat display
    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_history:
            st.markdown(
                """<div class="chat-ai">
                    👋 Hi! I'm <strong>EURON</strong>, your personal hydration coach.
                    Ask me anything about your water intake, hydration tips, or your progress!
                </div>""",
                unsafe_allow_html=True,
            )
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-user">🧑 {msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="chat-ai">🤖 {msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

    # Quick-prompt buttons
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Quick questions:**")
    qp_cols = st.columns(3)
    quick_prompts = [
        ("📊 My status today", "How am I doing with my water intake today?"),
        ("📅 Weekly summary", "Give me a summary of my water intake this week."),
        ("💡 Hydration tips", "Give me 3 tips to stay better hydrated throughout the day."),
    ]
    for i, (label, prompt) in enumerate(quick_prompts):
        with qp_cols[i]:
            if st.button(label, key=f"qp_{i}"):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.spinner("EURON is thinking…"):
                    response = agent.chat(
                        prompt,
                        history=[
                            (m["content"] if m["role"] == "user" else None)
                            for m in st.session_state.chat_history[:-1]
                        ],
                    )
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()

    # Free-form input
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Message EURON…",
            placeholder="e.g. How much more should I drink today?",
            label_visibility="collapsed",
        )
        send = st.form_submit_button("Send 🚀", use_container_width=False)

    if send and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("EURON is thinking…"):
            response = agent.chat(user_input)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

    if st.button("🗑 Clear Chat", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()
