import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")

# Vector DB Configuration
VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "chroma")
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./vector_db")

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_EMAIL = os.getenv("GITHUB_EMAIL")

# Project Configuration
PROJECT_PATH = Path("../keycloak-otp-password-authenticator").absolute()

# Ensure all required paths exist
Path(VECTOR_DB_PATH).mkdir(parents=True, exist_ok=True)
