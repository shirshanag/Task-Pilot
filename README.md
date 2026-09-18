# 🤖 AI Task Management Agent

An AI-powered task management agent that allows users to create, manage, query, and reason about tasks using natural language.

Instead of manually interacting with a database or navigating multiple CRUD controls, users can simply communicate with the agent. The agent interprets the request, selects the appropriate SQL tools, interacts with the task database, and returns a contextual response.

## ✨ Features

* 🗣️ **Natural Language Task Management** — Create, update, delete, and retrieve tasks using natural language.
* 🤖 **AI Agent** — Uses an LLM-powered agent to understand user intent and decide which tools to use.
* 🗄️ **SQL Database Integration** — Stores and manages tasks using SQLite.
* 🔧 **SQL Tool Calling** — Uses LangChain's SQL database toolkit to interact with the database.
* 🧠 **Contextual Reasoning** — Can reason over stored task information and answer questions about the user's tasks.
* 💬 **Conversational Memory** — Maintains conversation state using LangGraph's checkpointing.
* 📊 **Streamlit Interface** — Provides a simple interactive interface for communicating with the agent.
* 🔄 **CRUD Operations** — Supports task creation, retrieval, updating, and deletion.

## 🏗️ Architecture

```text
                    User
                      │
                      ▼
              ┌───────────────┐
              │   Streamlit   │
              │   Interface   │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │   AI Agent    │
              │  LangChain    │
              │  + LangGraph  │
              └───────┬───────┘
                      │
              ┌───────┴────────┐
              │                │
              ▼                ▼
        Groq LLM          SQL Tools
              │                │
              │                ▼
              │          ┌───────────┐
              │          │  SQLite   │
              │          │ Task DB   │
              │          └───────────┘
              │
              ▼
        Natural Language
           Response
```

## 🛠️ Tech Stack

| Technology               | Purpose                    |
| ------------------------ | -------------------------- |
| Python                   | Core programming language  |
| LangChain                | Agent and tool integration |
| LangGraph                | Agent state/checkpointing  |
| Groq                     | LLM inference              |
| `gpt-oss-20b`            | Language model             |
| SQLite                   | Task database              |
| Streamlit                | User interface             |
| SQLAlchemy / SQLDatabase | Database interaction       |

## 📂 Project Structure

```text
sql-agent/
│
├── app.py                  # Streamlit application
├── cli.py                  # CLI interface for the AI task management agent
├── my_task.db              # Local SQLite database
├── requirements.txt        # Python dependencies
├── .env                    # API credentials (not committed)
├── .gitignore
└── README.md
```

## ⚙️ How It Works

The application follows an agentic workflow:

```text
User Request
     ↓
LLM interprets intent
     ↓
Agent selects appropriate SQL tool
     ↓
SQL query is generated
     ↓
Database operation is executed
     ↓
Agent interprets the result
     ↓
Natural-language response
```

For example, a user can ask:

> "Show me my pending tasks."

The agent can inspect the database and retrieve the relevant records.

A request such as:

> "Mark my ML project as completed."

can be interpreted as an update operation and executed through the SQL tools.

The agent can also reason over retrieved task information. For example:

> "Which task should I complete first?"

The agent can inspect the available pending tasks and use information such as deadlines or descriptions to provide a contextual recommendation.

## 🗃️ Database Schema

The current task database contains:

```text
tasks
├── id
├── title
├── description
├── status
└── created_at
```

### Status Values

```text
pending
in_progress
completed
```

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/shirshanag/Task-Pilot
cd sql-agent
```

### 2. Create a virtual environment

```bash
python -m venv env
```

Activate it on Windows:

```bash
env\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
```

Do not commit your `.env` file to GitHub.

### 5. Run the application

For the Streamlit interface:

```bash
streamlit run app.py
```

The application will open in your browser.

## 💬 Example Interactions

### Create a task

```text
User:
Add a task to learn RAG.
```

### Retrieve tasks

```text
User:
Show me my pending tasks.
```

### Update a task

```text
User:
Mark the RAG task as completed.
```

### Reason about tasks

```text
User:
Which task should I complete first?
```

The agent retrieves the relevant task information and provides a contextual response.

### Ask about a project

```text
User:
What project do I need to work on?
```

The agent can inspect the stored tasks and identify the relevant project.

## 🔐 Environment Variables

The following environment variable is required:

```text
GROQ_API_KEY
```

Store API credentials in `.env` and keep the file excluded through `.gitignore`.

## 🎯 Project Goal

The goal of this project is to explore how **LLM agents, tool calling, databases, and conversational memory** can be combined to build a practical AI application.

Rather than using an LLM only for generating text, the agent is given access to tools that allow it to interact with real application data and perform actions based on natural-language requests.

## 🔮 Future Improvements

Potential improvements include:

* More robust task extraction
* Better handling of ambiguous task names
* Task filtering and search
* Improved error handling
* Authentication and user-specific task databases
* Calendar integration
* Task reminders and notifications
* Deployment with Docker
* Production database such as PostgreSQL

## 📌 Disclaimer

This project is built as an educational and portfolio project to explore agentic AI, LLM tool calling, and database interaction.

## 👨‍💻 Author

**Shirsha Nag**

B.Tech CSE — IoT & Cyber Security Including Blockchain Technology

Interested in **AI/ML, Agentic AI, Computer Vision, Quantum Computing, and AI Research**.
