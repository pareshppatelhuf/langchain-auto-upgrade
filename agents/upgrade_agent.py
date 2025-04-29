import logging
from typing import List, Dict, Any, Optional

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnablePassthrough
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_community.chat_models import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.tools import tool

from config.settings import LLM_PROVIDER, ANTHROPIC_API_KEY, OPENAI_API_KEY, ANTHROPIC_MODEL, OPENAI_MODEL
from tools.dependency_scanner import DependencyScanner
from tools.code_analysis import CodeAnalysisTool
from tools.git_operations import GitOperationsTool
from tools.compilation import CompilationTool
from tools.test_generator import TestGeneratorTool
from tools.vector_db import CodeVectorDB
from utils.message_formatter import MessageFormatter, Role

logger = logging.getLogger(__name__)

class UpgradeAgent:
    def __init__(self):
        self.vector_db = CodeVectorDB()
        self.tools = self._setup_tools()
        self.llm = self._setup_llm()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.agent_executor = self._setup_agent()
    
    def _setup_tools(self) -> List[Any]:
        """Set up the tools for the agent."""
        return [
            DependencyScanner()#,
            # CodeAnalysisTool(),
            # GitOperationsTool(),
            # CompilationTool(),
            # TestGeneratorTool()
        ]
    def _setup_llm(self) -> Any:
        """Set up the language model based on configuration."""
        if LLM_PROVIDER.lower() == "anthropic":
            return ChatAnthropic(
                model=ANTHROPIC_MODEL,
                anthropic_api_key=ANTHROPIC_API_KEY,
                temperature=0.5
            )
        else:
            # Remove proxies parameter as it's no longer supported in newer versions
            return ChatOpenAI(
                model=OPENAI_MODEL,
                openai_api_key=OPENAI_API_KEY,
                temperature=0.5
            )
    
    def _setup_agent(self) -> AgentExecutor:
        """Set up the agent with tools and LLM."""
        # Create system prompt
        system_prompt = """You are an expert software engineer specializing in dependency upgrades and code maintenance.
        Your task is to help upgrade dependencies in software projects, analyze the impact of these upgrades,
        implement necessary code changes, and validate the changes through testing.
        
        You have access to the following tools:
        1. dependency_scanner: Scans a project for dependencies and identifies upgrade candidates
        2. code_analysis: Analyzes and modifies code files, searches codebase for relevant code
        3. git_operations: Performs Git operations like creating branches, committing changes, pushing to remote, and creating pull requests
        4. compilation: Compiles the project and runs tests
        5. test_generator: Generates test cases for code files
        
        Follow these steps when upgrading dependencies:
        1. Scans a project for dependencies and identifies upgrade candidates
        2. For each upgrade candidate, analyze the potential impact on the codebase
        3. Create a new branch for the upgrade
        4. Implement necessary code changes to accommodate the upgrade
        5. Generate and update tests as needed
        6. Compile the project and run tests to validate changes
        7. If compilation or tests fail, fix the issues
        8. Once everything passes, commit the changes, push the branch, and create a pull request
        
        Always explain your reasoning and the changes you're making.
        """
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create agent
        agent = create_openai_functions_agent(self.llm, self.tools, prompt)
        
        # Create agent executor
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=False
        )
    
    def run(self, query: str) -> Dict[str, Any]:
        """Run the agent with a query."""
        logger.info(f"Running agent with query: {query}")
        
        # Format the query message
        formatted_query = MessageFormatter.format_message(Role.USER, query)
        print(formatted_query)
        
        # Run the agent
        #result = self.agent_executor(query)
        # print("*"*80)
        # print(type(self.agent_executor))
        # print(type(self.agent_executor.invoke))
        # print("*"*80)
        result = self.agent_executor.invoke({"input": query})
        
        # Format the response message
        formatted_response = MessageFormatter.format_message(Role.ASSISTANT, result["output"])
        print(formatted_response)
        
        return result
    
    def initialize_vector_db(self, force_refresh: bool = False) -> None:
        """Initialize the vector database."""
        logger.info("Initializing vector database")
        self.vector_db.embed_project(force_refresh=force_refresh)
        logger.info("Vector database initialization complete")
    
    def upgrade_dependency(self, dependency_name: str, target_version: Optional[str] = None) -> Dict[str, Any]:
        """Upgrade a specific dependency."""
        query = f"Upgrade the dependency {dependency_name}"
        if target_version:
            query += f" to version {target_version}"
        
        return self.run(query)
    
    def scan_and_upgrade_all(self) -> Dict[str, Any]:
        """Scan the project and upgrade all dependencies that need updating."""
        query = """
        Please scan the project for dependencies that need upgrading.
        For each dependency that needs an upgrade:
        1. Analyze the potential impact
        2. Create a separate branch for each upgrade
        3. Implement necessary code changes
        4. Generate and run tests
        5. Create a pull request for each successful upgrade
        
        Start by scanning the dependencies, then proceed with the upgrades one by one.
        """
        
        return self.run(query)
    
    def scan_and_find_upgrade_candidate(self) -> Dict[str, Any]:
        """Scan the project and find upgrade candidates."""
        query = "Scan the project for dependencies and find upgrade candidates."
        query = "find upgrade candidates"
        logger.info("Scanning for upgrade candidates...")
        return self.run(query)

    