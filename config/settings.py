import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# LLM Configuration
LLM_PROVIDER="openai" # anthropic or openai
ANTHROPIC_API_KEY="<<>>"
OPENAI_API_KEY="<<>>"
ANTHROPIC_MODEL="claude-3-7-sonnet-20250219"
OPENAI_MODEL="gpt-4-turbo"

# LLM API Configuration


# Vector DB Configuration
VECTOR_DB_TYPE="chroma"  # or pinecone, qdrant, etc.
VECTOR_DB_PATH="./vector_db"

# GitHub Configuration
GITHUB_TOKEN="<<>>"
GITHUB_USERNAME="<<>>"
GITHUB_EMAIL="<<>>"

# Get the project root directory
REPO_LOCAL_PATH = Path("<<>>").absolute()

# Ensure all required paths exist
Path(VECTOR_DB_PATH).mkdir(parents=True, exist_ok=True)
