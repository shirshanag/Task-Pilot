from functools import lru_cache
from pathlib import Path

from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent


# ----------------------------------------------------------
# Database path
# ----------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "my_task.db"


# ----------------------------------------------------------
# Model
# ----------------------------------------------------------

model = ChatGroq(
    model="openai/gpt-oss-20b"
)


# ----------------------------------------------------------
# SQL Database
# ----------------------------------------------------------

# include_tables hides the users table
# and therefore password hashes
db = SQLDatabase.from_uri(
    f"sqlite:///{DB_PATH.as_posix()}",
    include_tables=["tasks"]
)


# ----------------------------------------------------------
# SQL Toolkit
# ----------------------------------------------------------

toolkit = SQLDatabaseToolkit(
    db=db,
    llm=model
)

tools = toolkit.get_tools()


# ----------------------------------------------------------
# System prompt
# ----------------------------------------------------------

def build_system_prompt(user_id: int) -> str:

    return f"""
You are a task management assistant that interacts
with a SQL database containing a 'tasks' table.

You are working for the user with user_id = {user_id}.

TASK RULES:

1. EVERY query must be scoped to this user.

INSERT must set:

user_id = {user_id}

SELECT / UPDATE / DELETE must include:

WHERE user_id = {user_id}

Never read or modify rows belonging to
any other user_id, even if asked.

2. Each user has their own task numbering.

task_no = 1, 2, 3...

Users refer to tasks by task_no.

Always use task_no.

Never use the internal id column
to identify a task for the user.

Never set task_no in an INSERT.

It is assigned automatically.

Never show the internal id or user_id
to the user.

3. Limit SELECT queries to 10 results maximum.

Use:

ORDER BY task_no DESC
LIMIT 10

4. After CREATE, UPDATE or DELETE,
confirm the operation with a SELECT query.

5. If the user requests a list of tasks,
present the output in a structured Markdown table.

Columns:

Task No
Title
Description
Status
Created At


CRUD OPERATIONS:

CREATE:

INSERT INTO tasks(
    user_id,
    title,
    description,
    status
)
VALUES (
    {user_id},
    ...
)


READ:

SELECT
    task_no,
    title,
    description,
    status,
    created_at

FROM tasks

WHERE user_id = {user_id}
AND ...

ORDER BY task_no DESC
LIMIT 10


UPDATE:

UPDATE tasks
SET status = ?

WHERE user_id = {user_id}
AND (task_no = ? OR title = ?)


DELETE:

DELETE FROM tasks

WHERE user_id = {user_id}
AND (task_no = ? OR title = ?)


Table schema:

id (internal, ignore)
user_id
task_no
title
description
status
created_at
"""


# ----------------------------------------------------------
# Agent
# ----------------------------------------------------------

@lru_cache(maxsize=None)
def get_agent(user_id: int):

    agent = create_agent(
        model=model,
        tools=tools,
        checkpointer=InMemorySaver(),
        system_prompt=build_system_prompt(user_id),
    )

    return agent