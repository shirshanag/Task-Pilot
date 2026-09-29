from dotenv import load_dotenv
load_dotenv()

import warnings

warnings.filterwarnings(
    "ignore",
    message="`langchain-community` is being sunset"
)

import streamlit as st
from html import escape

# ----------------------------------------------------------------------
# Backend imports
# ----------------------------------------------------------------------
from backend.auth import login_user, signup_user
from backend.history import load_history, save_message
from backend.tasks import get_tasks
from backend.agent import get_agent


# ----------------------------------------------------------------------
# UI: theme
# ----------------------------------------------------------------------
st.set_page_config(page_title="TaskPilot AI", page_icon="✨", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #0a0e1a; --surface: #111827; --surface-2: #161f33; --border: #1f2a44;
    --text: #e6eaf5; --muted: #8b97b5;
    --accent: #7c5cff; --accent-2: #22d3ee;
    --pending: #f59e0b; --progress: #3b82f6; --done: #10b981;
}
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; color: var(--text); }
.stApp {
    background:
        radial-gradient(900px 500px at 8% -10%, rgba(124,92,255,.18), transparent 60%),
        radial-gradient(800px 500px at 100% 0%, rgba(34,211,238,.12), transparent 55%),
        var(--bg);
}
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1250px; }

/* Sidebar */
[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }
[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }

/* Brand */
.brand { display:flex; align-items:center; gap:10px; font-weight:800; font-size:1.25rem; letter-spacing:-.02em; }
.brand-logo { width:34px; height:34px; border-radius:10px; display:grid; place-items:center;
    background: linear-gradient(135deg, var(--accent), var(--accent-2)); box-shadow: 0 6px 20px rgba(124,92,255,.4); }
.grad { background: linear-gradient(90deg, var(--accent), var(--accent-2)); -webkit-background-clip:text;
    background-clip:text; color:transparent; }

/* Hero */
.badge { display:inline-block; padding:6px 12px; border-radius:999px; font-size:.78rem; font-weight:600;
    color:var(--accent-2); background:rgba(34,211,238,.08); border:1px solid rgba(34,211,238,.25); }
.hero h1 { font-size:3rem; line-height:1.1; font-weight:800; letter-spacing:-.03em; margin:18px 0 14px; }
.hero p { color:var(--muted); font-size:1.05rem; max-width:520px; line-height:1.6; }
.feat { display:flex; gap:14px; align-items:flex-start; padding:14px 16px; margin-top:12px; max-width:520px;
    background:rgba(17,24,39,.7); border:1px solid var(--border); border-radius:14px; backdrop-filter: blur(6px); }
.feat .ic { font-size:1.3rem; }
.feat b { display:block; font-size:.95rem; } .feat span { color:var(--muted); font-size:.85rem; }

/* Auth card (form) */
[data-testid="stForm"] { background:var(--surface); border:1px solid var(--border); border-radius:16px; padding:22px; }
.auth-title { font-size:1.5rem; font-weight:700; margin-bottom:2px; }
.auth-sub { color:var(--muted); font-size:.9rem; margin-bottom:10px; }

/* Inputs */
.stTextInput input { background:var(--surface-2) !important; border:1px solid var(--border) !important;
    border-radius:10px !important; color:var(--text) !important; }
.stTextInput input:focus { border-color:var(--accent) !important; box-shadow:0 0 0 3px rgba(124,92,255,.2) !important; }

/* Buttons */
.stButton > button, [data-testid="stFormSubmitButton"] > button {
    border-radius:10px; border:1px solid var(--border); background:var(--surface-2); color:var(--text);
    font-weight:600; transition: all .15s ease; }
.stButton > button:hover { border-color:var(--accent); color:#fff; transform: translateY(-1px); }
[data-testid="stFormSubmitButton"] > button {
    width:100%; border:none; color:#fff; background: linear-gradient(90deg, var(--accent), #5b8def);
    box-shadow: 0 8px 22px rgba(124,92,255,.35); }
[data-testid="stFormSubmitButton"] > button:hover { filter:brightness(1.1); transform: translateY(-1px); }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap:6px; border-bottom:1px solid var(--border); }
.stTabs [data-baseweb="tab"] { background:transparent; border-radius:10px 10px 0 0; padding:10px 18px;
    color:var(--muted); font-weight:600; }
.stTabs [aria-selected="true"] { color:#fff !important; }
.stTabs [data-baseweb="tab-highlight"] { background: linear-gradient(90deg, var(--accent), var(--accent-2)); }

/* Stat cards */
.stats { display:grid; grid-template-columns: repeat(4, 1fr); gap:14px; margin: 6px 0 18px; }
.stat { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:16px 18px;
    position:relative; overflow:hidden; }
.stat::before { content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--c, var(--accent)); }
.stat-label { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.06em; font-weight:600; }
.stat-value { font-size:2rem; font-weight:800; margin-top:4px; letter-spacing:-.02em; }
.stat.pending { --c: var(--pending); } .stat.progress { --c: var(--progress); } .stat.done { --c: var(--done); }

/* Sidebar user + progress */
.user-chip { display:flex; align-items:center; gap:10px; padding:10px 12px; margin:14px 0;
    background:var(--surface-2); border:1px solid var(--border); border-radius:12px; }
.avatar { width:34px; height:34px; border-radius:50%; display:grid; place-items:center; font-weight:700;
    background: linear-gradient(135deg, var(--accent), var(--accent-2)); }
.user-chip small { color:var(--muted); display:block; font-size:.72rem; }
.section-label { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.08em;
    font-weight:700; margin:18px 0 8px; }
.bar { height:8px; border-radius:99px; background:var(--surface-2); overflow:hidden; border:1px solid var(--border); }
.bar > div { height:100%; background: linear-gradient(90deg, var(--accent), var(--accent-2)); }

/* Chat */
[data-testid="stChatMessage"] { background:var(--surface); border:1px solid var(--border); border-radius:14px;
    padding:14px 16px; margin-bottom:10px; }
[data-testid="stChatMessage"] table { width:100%; border-collapse:collapse; font-size:.9rem; }
[data-testid="stChatMessage"] th { background:var(--surface-2); color:var(--muted); text-transform:uppercase;
    font-size:.72rem; letter-spacing:.06em; }
[data-testid="stChatMessage"] th, [data-testid="stChatMessage"] td { border:1px solid var(--border); padding:8px 10px; }
[data-testid="stChatInput"] { border-radius:14px; border:1px solid var(--border); background:var(--surface); }
[data-testid="stChatInput"]:focus-within { border-color:var(--accent); box-shadow:0 0 0 3px rgba(124,92,255,.2); }
.welcome { text-align:center; padding:38px 20px; border:1px dashed var(--border); border-radius:16px;
    background:rgba(17,24,39,.5); }
.welcome h3 { margin:0 0 6px; font-size:1.3rem; } .welcome p { color:var(--muted); margin:0; }

/* Board */
.col-head { display:flex; justify-content:space-between; align-items:center; padding:10px 14px; margin-bottom:10px;
    border-radius:12px; font-weight:700; background:var(--surface); border:1px solid var(--border);
    border-top:3px solid var(--c); }
.col-head span { background:var(--surface-2); border-radius:99px; padding:2px 10px; font-size:.8rem; color:var(--muted); }
.col-head.pending { --c: var(--pending); } .col-head.progress { --c: var(--progress); } .col-head.done { --c: var(--done); }
.tcard { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px; margin-bottom:10px;
    transition: all .15s ease; }
.tcard:hover { border-color:var(--accent); transform: translateY(-2px); box-shadow:0 10px 24px rgba(0,0,0,.35); }
.tcard .no { color:var(--accent-2); font-size:.72rem; font-weight:700; letter-spacing:.06em; }
.tcard .ttl { font-weight:600; margin:4px 0; }
.tcard .dsc { color:var(--muted); font-size:.85rem; line-height:1.45; }
.tcard .dt { color:var(--muted); font-size:.72rem; margin-top:10px; }
.empty { text-align:center; color:var(--muted); font-size:.85rem; padding:22px; border:1px dashed var(--border);
    border-radius:12px; }

@media (max-width: 800px) { .stats { grid-template-columns: repeat(2, 1fr); } .hero h1 { font-size:2.2rem; } }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

BRAND = '<div class="brand"><div class="brand-logo">✨</div><span>TaskPilot <span class="grad">AI</span></span></div>'


# ----------------------------------------------------------------------
# UI: helpers
# ----------------------------------------------------------------------
def stat_card(label, value, cls=""):
    return f'<div class="stat {cls}"><div class="stat-label">{label}</div><div class="stat-value">{value}</div></div>'
def html(s: str) -> str:
    """Strip indentation and blank lines so Markdown never treats HTML as a code block."""
    return "".join(line.strip() for line in s.splitlines() if line.strip())

def task_card(t):
    desc = escape(t["description"] or "No description")
    date = (t["created_at"] or "")[:10]

    return (
        f'<div class="tcard"><div class="no">TASK #{t["task_no"]}</div>'
        f'<div class="ttl">{escape(t["title"])}</div><div class="dsc">{desc}</div>'
        f'<div class="dt">Created {date}</div></div>'
    )


# ----------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None


# ----------------------------------------------------------------------
# UI: landing + login / signup
# ----------------------------------------------------------------------
if st.session_state.user is None:

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        st.markdown(
            html(
            BRAND
            + """
            <div class="hero">
                <span class="badge">● AI-powered task management</span>
                <h1>Run your work by <span class="grad">just talking</span> to it.</h1>
                <p>Create, update and track tasks in plain English. TaskPilot turns your messages
                into organized work, and keeps everything right where you left it.</p>

                <div class="feat">
                    <div class="ic">💬</div>
                    <div>
                        <b>Natural-language control</b>
                        <span>"Add a task to prepare Friday's demo", done.</span>
                    </div>
                </div>

                <div class="feat">
                    <div class="ic">📋</div>
                    <div>
                        <b>Live task board</b>
                        <span>See pending, in-progress and completed work at a glance.</span>
                    </div>
                </div>

                <div class="feat">
                    <div class="ic">🔒</div>
                    <div>
                        <b>Private workspace</b>
                        <span>Your tasks and conversations are yours, resumed on every login.</span>
                    </div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    with right:
        st.markdown(
            '<div class="auth-title">Welcome</div>'
            '<div class="auth-sub">Log in or create an account to continue.</div>',
            unsafe_allow_html=True,
        )

        login_tab, signup_tab = st.tabs(["Login", "Sign up"])

        with login_tab:
            with st.form("login_form"):
                l_user = st.text_input("Username")
                l_pass = st.text_input("Password", type="password")

                if st.form_submit_button("Log in"):
                    user = login_user(l_user, l_pass)

                    if user:
                        st.session_state.user = user
                        st.session_state.history = load_history(user["id"])
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with signup_tab:
            with st.form("signup_form"):
                s_user = st.text_input("Choose a username")
                s_pass = st.text_input("Choose a password", type="password")
                s_pass2 = st.text_input("Confirm password", type="password")

                if st.form_submit_button("Create account"):

                    if s_pass != s_pass2:
                        st.error("Passwords do not match.")

                    else:
                        ok, msg = signup_user(s_user, s_pass)
                        (st.success if ok else st.error)(msg)

    st.stop()


# ----------------------------------------------------------------------
# UI: dashboard (logged in)
# ----------------------------------------------------------------------
user = st.session_state.user

tasks = get_tasks(user["id"])

total = len(tasks)
n_pending = sum(t["status"] == "pending" for t in tasks)
n_progress = sum(t["status"] == "in_progress" for t in tasks)
n_done = sum(t["status"] == "completed" for t in tasks)

pct = int(n_done / total * 100) if total else 0


# ----------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------
with st.sidebar:

    st.markdown(BRAND, unsafe_allow_html=True)

    st.markdown(
        f'<div class="user-chip">'
        f'<div class="avatar">{escape(user["username"][:1].upper())}</div>'
        f'<div><b>{escape(user["username"])}</b>'
        f'<small>Personal workspace</small></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="section-label">Completion · {pct}%</div>'
        f'<div class="bar"><div style="width:{pct}%"></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-label">Quick actions</div>',
        unsafe_allow_html=True,
    )

    quick_actions = {
        "📋 Show all my tasks": "Show all my tasks",
        "⏳ What's pending?": "Show my pending tasks",
        "🚧 What's in progress?": "Show my in-progress tasks",
        "✅ Show completed": "Show my completed tasks",
    }

    for label, text in quick_actions.items():

        if st.button(
            label,
            use_container_width=True,
            key=f"qa_{label}",
        ):
            st.session_state.quick_prompt = text

    st.markdown(
        '<div class="section-label">Account</div>',
        unsafe_allow_html=True,
    )

    if st.button("Log out", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# ----------------------------------------------------------------------
# Dashboard header
# ----------------------------------------------------------------------
st.markdown(
    '<h2 style="margin:0 0 4px;font-weight:800;letter-spacing:-.02em;">'
    f'Hello, {escape(user["username"].title())} 👋</h2>'
    '<p style="color:#8b97b5;margin:0 0 14px;">Here\'s where your work stands today.</p>',
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# Stats
# ----------------------------------------------------------------------
st.markdown(
    '<div class="stats">'
    + stat_card("Total tasks", total)
    + stat_card("Pending", n_pending, "pending")
    + stat_card("In progress", n_progress, "progress")
    + stat_card("Completed", n_done, "done")
    + "</div>",
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# Chat prompt
# ----------------------------------------------------------------------
quick = st.session_state.pop("quick_prompt", None)

prompt = (
    st.chat_input(
        "Ask me to manage your tasks, e.g. “Add a task to review the Q3 report”"
    )
    or quick
)


# ----------------------------------------------------------------------
# Chat history
# ----------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = load_history(user["id"])


# ----------------------------------------------------------------------
# Agent
# ----------------------------------------------------------------------
agent = get_agent(user["id"])


# ----------------------------------------------------------------------
# Tabs
# ----------------------------------------------------------------------
tab_chat, tab_board = st.tabs(
    ["💬 AI Assistant", "📋 Task Board"]
)


# ----------------------------------------------------------------------
# AI Assistant
# ----------------------------------------------------------------------
with tab_chat:

    if not st.session_state.history and not prompt:

        st.markdown(
            f'<div class="welcome">'
            f'<h3>Hi {escape(user["username"].title())}, I\'m your task copilot ✨</h3>'
            "<p>Try: “Add a high-priority task to prepare the demo” · "
            "“Mark task 2 as completed” · "
            "“Show my pending tasks”</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    # Existing conversation
    for message in st.session_state.history:

        role = message["role"]
        content = message["content"]

        st.chat_message(
            role,
            avatar="✨" if role == "ai" else "👤"
        ).markdown(content)

    # New prompt
    if prompt:

        st.chat_message(
            "user",
            avatar="👤"
        ).markdown(prompt)

        st.session_state.history.append({
            "role": "user",
            "content": prompt
        })

        save_message(
            user["id"],
            "user",
            prompt
        )

        with st.chat_message("ai", avatar="✨"):

            with st.spinner("Processing..."):

                response = agent.invoke(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    },
                    {
                        "configurable": {
                            "thread_id": f"user-{user['id']}"
                        }
                    }
                )

                result = response["messages"][-1].content

                st.markdown(result)

                st.session_state.history.append({
                    "role": "ai",
                    "content": result
                })

                save_message(
                    user["id"],
                    "ai",
                    result
                )

        # Refresh stats and board
        st.rerun()


# ----------------------------------------------------------------------
# Task Board
# ----------------------------------------------------------------------
with tab_board:

    columns = [
        ("pending", "⏳ Pending", "pending"),
        ("in_progress", "🚧 In Progress", "progress"),
        ("completed", "✅ Completed", "done"),
    ]

    for col, (key, label, cls) in zip(
        st.columns(3, gap="medium"),
        columns
    ):

        items = [
            t for t in tasks
            if t["status"] == key
        ]

        body = (
            "".join(task_card(t) for t in items)
            or '<div class="empty">Nothing here yet</div>'
        )

        col.markdown(
            f'<div class="col-head {cls}">'
            f'{label}<span>{len(items)}</span>'
            f'</div>{body}',
            unsafe_allow_html=True,
        )