from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools.dependency_scanner import DependencyScanner
from tools.code_analysis import CodeAnalysisTool
# Define tools properly with decorators
@tool
def search_database(query: str) -> str:
    """Search the database for information."""
    # Implementation
    return f"Results for: {query}"

# Ensure your LLM is configured for function calling
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0
)

# Create a proper prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant that uses tools when necessary."),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# Create the agent with functions explicitly
tools = [DependencyScanner(),
            CodeAnalysisTool()]
agent = create_openai_functions_agent(llm, tools, prompt)

# Create the executor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Now invoke
result = agent_executor.invoke({"input": "find upgrade candidates"})