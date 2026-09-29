import langchain
import streamlit 
import langgraph
from importlib.metadata import version
print(streamlit.__version__)


print("LangGraph:", version("langgraph"))
print("LangChain:", version("langchain"))
print("LangChain Core:", version("langchain-core"))
print("LangChain Groq:", version("langchain-groq"))
print("Langchain Community:",version("langchain_community"))