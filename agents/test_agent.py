import logging
from typing import List, Dict, Any, Optional

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage, HumanMessage
from langchain_community.chat_models import ChatAnthropic
from langchain_openai import ChatOpenAI

from config.settings import LLM_PROVIDER, ANTHROPIC_API_KEY, OPENAI_API_KEY, ANTHROPIC_MODEL, OPENAI_MODEL
from tools.code_analysis import CodeAnalysisTool
from tools.test_generator import TestGeneratorTool
from tools.compilation import CompilationTool
from tools.vector_db import CodeVectorDB
from utils.message_formatter import MessageFormatter, Role

logger = logging.getLogger(__name__)

class TestAgent:
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
            CodeAnalysisTool(),
            TestGeneratorTool(),
            CompilationTool()
        ]
    
    def _setup_llm(self) -> Any:
        """Set up the language model based on configuration."""
        if LLM_PROVIDER.lower() == "anthropic":
            return ChatAnthropic(
                model=ANTHROPIC_MODEL,
                anthropic_api_key=ANTHROPIC_API_KEY,
                temperature=0.2
            )
        else:
            return ChatOpenAI(
                model=OPENAI_MODEL,
                openai_api_key=OPENAI_API_KEY,
                temperature=0.2
            )
    
    def _setup_agent(self) -> AgentExecutor:
        """Set up the agent with tools and LLM."""
        # Create system prompt
        system_prompt = """You are an expert test engineer specializing in creating comprehensive test suites for software projects.
        Your task is to analyze code files, generate appropriate test cases, and validate the tests through execution.
        
        You have access to the following tools:
        1. code_analysis: Analyzes code files, searches codebase for relevant code
        2. test_generator: Generates test cases for code files
        3. compilation: Compiles the project and runs tests
        
        Follow these steps when generating tests:
        1. Analyze the code file to understand its structure and functionality
        2. Identify the appropriate test framework to use
        3. Generate comprehensive test cases that cover normal operation, edge cases, and error conditions
        4. Run the tests to ensure they pass
        5. If tests fail, diagnose the issues and fix the tests
        
        Always explain your reasoning and the approach you're taking for testing.
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
            handle_parsing_errors=True
        )
    
    def run(self, query: str) -> Dict[str, Any]:
        """Run the agent with a query."""
        logger.info(f"Running agent with query: {query}")
        
        # Format the query message
        formatted_query = MessageFormatter.format_message(Role.USER, query)
        print(formatted_query)
        
        # Run the agent
        result = self.agent_executor.invoke({"input": query})
        
        # Format the response message
        formatted_response = MessageFormatter.format_message(Role.ASSISTANT, result["output"])
        print(formatted_response)
        
        return result
    
    def generate_tests_for_file(self, file_path: str, test_framework: Optional[str] = None, 
                              output_path: Optional[str] = None) -> Dict[str, Any]:
        """Generate tests for a specific file."""
        query = f"Generate tests for the file {file_path}"
        if test_framework:
            query += f" using the {test_framework} framework"
        if output_path:
            query += f" and save them to {output_path}"
        
        return self.run(query)
    
    def run_tests(self, test_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run tests for the project or specific test files."""
        if test_files:
            query = f"Run the following test files: {', '.join(test_files)}"
        else:
            query = "Run all tests for the project"
        
        return self.run(query)
