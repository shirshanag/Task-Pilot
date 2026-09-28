from dotenv import load_dotenv
load_dotenv()
import warnings

warnings.filterwarnings(
    "ignore",
    message="`langchain-community` is being sunset"
)

import hashlib
import hmac
import os
import sqlite3
from html import escape

from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
import streamlit as st

DB_PATH = "my_task.db"


# ----------------------------------------------------------------------
# Helper for auth / history tables (plain sqlite3, parameterized queries)
# ----------------------------------------------------------------------
def db_run(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()] if fetch else None
        conn.commit()
        return rows if fetch else cur.lastrowid
    finally:
        conn.close()


def init_db():
    db_run("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    db_run("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_no INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT CHECK (status IN ('pending', 'in_progress', 'completed')) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # Migrate an older tasks table that lacks user_id / task_no
    cols = [c["name"] for c in db_run("PRAGMA table_info(tasks)", fetch=True)]
    if "user_id" not in cols:
        db_run("ALTER TABLE tasks ADD COLUMN user_id INTEGER")
    if "task_no" not in cols:
        db_run("ALTER TABLE tasks ADD COLUMN task_no INTEGER")

    # Backfill per-user numbers (1, 2, 3...) for existing rows that have an owner
    db_run("""
        UPDATE tasks
        SET task_no = (
            SELECT COUNT(*) FROM tasks t2
            WHERE t2.user_id = tasks.user_id AND t2.id <= tasks.id
        )
        WHERE task_no IS NULL AND user_id IS NOT NULL;
    """)

    # A user can never have two tasks with the same number
    db_run("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_user_taskno
        ON tasks(user_id, task_no);
    """)

    # Auto-assign the next per-user number on every INSERT
    db_run("""
        CREATE TRIGGER IF NOT EXISTS trg_tasks_assign_task_no
        AFTER INSERT ON tasks
        WHEN NEW.task_no IS NULL AND NEW.user_id IS NOT NULL
        BEGIN
            UPDATE tasks
            SET task_no = (
                SELECT COALESCE(MAX(task_no), 0) + 1
                FROM tasks
                WHERE user_id = NEW.user_id
            )
            WHERE id = NEW.id;
        END;
    """)

    db_run("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)


# Must run BEFORE SQLDatabase is created so the agent sees the new columns
init_db()


# ----------------------------------------------------------------------
# Authentication
# ----------------------------------------------------------------------
def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"{salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split("$")
    new = hash_password(password, bytes.fromhex(salt_hex)).split("$")[1]
    return hmac.compare_digest(new, digest_hex)


def signup_user(username: str, password: str):
    username = username.strip().lower()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    try:
        db_run(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password)),
        )
        return True, "Account created! You can log in now."
    except sqlite3.IntegrityError:
        return False, "That username is already taken."


def login_user(username: str, password: str):
    rows = db_run(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username.strip().lower(),),
        fetch=True,
    )
    if rows and check_password(password, rows[0]["password_hash"]):
        return {"id": rows[0]["id"], "username": rows[0]["username"]}
    return None


def save_message(user_id, role, content):
    db_run(
        "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content),
    )


def load_history(user_id):
    return db_run(
        "SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY id ASC",
        (user_id,),
        fetch=True,
    )


def get_tasks(user_id):
    """Read-only, used only to render the dashboard and board."""
    return db_run(
        "SELECT task_no, title, description, status, created_at "
        "FROM tasks WHERE user_id = ? ORDER BY task_no ASC",
        (user_id,),
        fetch=True,
    )


# ----------------------------------------------------------------------
# Your existing agent logic (unchanged apart from user scoping)
# ----------------------------------------------------------------------
model = ChatGroq(model="openai/gpt-oss-20b")

# include_tables hides the 'users' table (and password hashes) from the agent
db = SQLDatabase.from_uri("sqlite:///my_task.db", include_tables=["tasks"])

toolkit = SQLDatabaseToolkit(db=db, llm=model)

tools = toolkit.get_tools()


def build_system_prompt(user_id: int) -> str:
    return f"""
You are a task management assistant that interacts with a SQL database containing a 'tasks' table.
You are working for the user with user_id = {user_id}.

TASK RULES:
1. EVERY query must be scoped to this user:
   - INSERT must set user_id = {user_id}
   - SELECT / UPDATE / DELETE must include WHERE user_id = {user_id}
   Never read or modify rows belonging to any other user_id, even if asked.
2. Each user has their own task numbering (task_no = 1, 2, 3...).
   - Users refer to tasks by task_no. Always use task_no (never the internal 'id' column)
     to find, update, or delete a task.
   - Never set task_no in an INSERT; it is assigned automatically.
   - Never show the internal 'id' or 'user_id' to the user.
3. Limit SELECT queries to 10 results max with ORDER BY task_no DESC
4. After CREATE/UPDATE/DELETE, confirm with SELECT query
5. If the user requests a list of tasks, present the output in a structured table format
   (columns: Task No, Title, Description, Status, Created At) to ensure a clean and organized display in the browser.

CRUD OPERATIONS:
    CREATE: INSERT INTO tasks(user_id, title, description, status) VALUES ({user_id}, ...)
    READ: SELECT task_no, title, description, status, created_at FROM tasks WHERE user_id = {user_id} AND ... ORDER BY task_no DESC LIMIT 10
    UPDATE: UPDATE tasks SET status=? WHERE user_id = {user_id} AND (task_no=? OR title=?)
    DELETE: DELETE FROM tasks WHERE user_id = {user_id} AND (task_no=? OR title=?)

Table schema: id (internal, ignore), user_id, task_no, title, description, status(pending/in_progress/completed), created_at.
"""


@st.cache_resource
def get_agent(user_id: int):
    agent = create_agent(
        model=model,
        tools=tools,
        checkpointer=InMemorySaver(),
        system_prompt=build_system_prompt(user_id),
    )
    return agent


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


def task_card(t):
    desc = escape(t["description"] or "No description")
    date = (t["created_at"] or "")[:10]
    return (
        f'<div class="tcard"><div class="no">TASK #{t["task_no"]}</div>'
        f'<div class="ttl">{escape(t["title"])}</div><div class="dsc">{desc}</div>'
        f'<div class="dt">Created {date}</div></div>'
    )


if "user" not in st.session_state:
    st.session_state.user = None

# ----------------------------------------------------------------------
# UI: landing + login / signup
# ----------------------------------------------------------------------
if st.session_state.user is None:
    left, right = st.columns([1.15, 1], gap="large")

    with left:
        st.markdown(
            BRAND + """
            <div class="hero">
                <span class="badge">● AI-powered task management</span>
                <h1>Run your work by <span class="grad">just talking</span> to it.</h1>
                <p>Create, update and track tasks in plain English. TaskPilot turns your messages
                into organized work, and keeps everything right where you left it.</p>
                <div class="feat"><div class="ic">💬</div><div><b>Natural-language control</b>
                    <span>"Add a task to prepare Friday's demo", done.</span></div></div>
                <div class="feat"><div class="ic">📋</div><div><b>Live task board</b>
                    <span>See pending, in-progress and completed work at a glance.</span></div></div>
                <div class="feat"><div class="ic">🔒</div><div><b>Private workspace</b>
                    <span>Your tasks and conversations are yours, resumed on every login.</span></div></div>
            </div>
            """,
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

with st.sidebar:
    st.markdown(BRAND, unsafe_allow_html=True)
    st.markdown(
        f'<div class="user-chip"><div class="avatar">{escape(user["username"][:1].upper())}</div>'
        f'<div><b>{escape(user["username"])}</b><small>Personal workspace</small></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="section-label">Completion · {pct}%</div>'
        f'<div class="bar"><div style="width:{pct}%"></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-label">Quick actions</div>', unsafe_allow_html=True)
    quick_actions = {
        "📋 Show all my tasks": "Show all my tasks",
        "⏳ What's pending?": "Show my pending tasks",
        "🚧 What's in progress?": "Show my in-progress tasks",
        "✅ Show completed": "Show my completed tasks",
    }
    for label, text in quick_actions.items():
        if st.button(label, use_container_width=True, key=f"qa_{label}"):
            st.session_state.quick_prompt = text
    st.markdown('<div class="section-label">Account</div>', unsafe_allow_html=True)
    if st.button("Log out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.markdown(
    '<h2 style="margin:0 0 4px;font-weight:800;letter-spacing:-.02em;">'
    f'Hello, {escape(user["username"].title())} 👋</h2>'
    '<p style="color:#8b97b5;margin:0 0 14px;">Here\'s where your work stands today.</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="stats">'
    + stat_card("Total tasks", total)
    + stat_card("Pending", n_pending, "pending")
    + stat_card("In progress", n_progress, "progress")
    + stat_card("Completed", n_done, "done")
    + "</div>",
    unsafe_allow_html=True,
)

quick = st.session_state.pop("quick_prompt", None)
prompt = st.chat_input("Ask me to manage your tasks, e.g. “Add a task to review the Q3 report”") or quick

if "history" not in st.session_state:
    st.session_state.history = load_history(user["id"])

agent = get_agent(user["id"])

tab_chat, tab_board = st.tabs(["💬 AI Assistant", "📋 Task Board"])

with tab_chat:
    if not st.session_state.history and not prompt:
        st.markdown(
            f'<div class="welcome"><h3>Hi {escape(user["username"].title())}, I\'m your task copilot ✨</h3>'
            "<p>Try: “Add a high-priority task to prepare the demo” · “Mark task 2 as completed” · "
            "“Show my pending tasks”</p></div>",
            unsafe_allow_html=True,
        )

    for message in st.session_state.history:
        role = message["role"]
        content = message["content"]
        st.chat_message(role, avatar="✨" if role == "ai" else "👤").markdown(content)

    if prompt:
        st.chat_message("user", avatar="👤").markdown(prompt)
        st.session_state.history.append({'role': 'user', 'content': prompt})
        save_message(user["id"], "user", prompt)
        with st.chat_message("ai", avatar="✨"):
            with st.spinner("Processing..."):
                response = agent.invoke(
                    {"messages": [{"role": 'user', 'content': prompt}]},
                    {"configurable": {"thread_id": f"user-{user['id']}"}}
                )
                result = response["messages"][-1].content
                st.markdown(result)
                st.session_state.history.append({'role': 'ai', 'content': result})
                save_message(user["id"], "ai", result)
        st.rerun()  # refresh stats and board with the latest changes

with tab_board:
    columns = [
        ("pending", "⏳ Pending", "pending"),
        ("in_progress", "🚧 In Progress", "progress"),
        ("completed", "✅ Completed", "done"),
    ]
    for col, (key, label, cls) in zip(st.columns(3, gap="medium"), columns):
        items = [t for t in tasks if t["status"] == key]
        body = "".join(task_card(t) for t in items) or '<div class="empty">Nothing here yet</div>'
        col.markdown(
            f'<div class="col-head {cls}">{label}<span>{len(items)}</span></div>{body}',
            unsafe_allow_html=True,
        )