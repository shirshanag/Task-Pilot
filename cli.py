from dotenv import load_dotenv
load_dotenv()
import warnings

warnings.filterwarnings(
    "ignore",
    message="`langchain-community` is being sunset"
)

## db,llm,tools,create_agent,system_prompt

from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent

model=ChatGroq(model="openai/gpt-oss-20b")

db=SQLDatabase.from_uri("sqlite:///my_task.db")

db.run("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT CHECK (status IN ('pending', 'in_progress', 'completed')) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       );
""")

toolkit=SQLDatabaseToolkit(db=db,llm=model)

tools=toolkit.get_tools()

system_prompt = """
You are a task management assistant that interacts with a SQL database containing a 'tasks' table. 

TASK RULES:
1. Limit SELECT queries to 10 results max with ORDER BY created_at DESC
2. After CREATE/UPDATE/DELETE, confirm with SELECT query
3. If the user requests a list of tasks, present the output in a structured table format to ensure a clean and organized display in the browser."

CRUD OPERATIONS:
    CREATE: INSERT INTO tasks(title, description, status)
    READ: SELECT * FROM tasks WHERE ... LIMIT 10
    UPDATE: UPDATE tasks SET status=? WHERE id=? OR title=?
    DELETE: DELETE FROM tasks WHERE id=? OR title=?

Table schema: id, title, description, status(pending/in_progress/completed), created_at.
"""
memory=InMemorySaver()

agent=create_agent(
    model=model,
    tools=tools,
    checkpointer=memory,
    system_prompt=system_prompt
)

while True:
    query=input("User: ")
    l=["bye","tata"]
    if query in l:
        break
    response=agent.invoke(
        {"messages":[{"role":'user','content':query}]},
        {"configurable":{"thread_id":1}}
                    
        )
    result=response["messages"][-1].content
    print("Ai: ",result)