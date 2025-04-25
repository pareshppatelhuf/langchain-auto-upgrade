import os
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from config.settings import PROJECT_PATH, LLM_PROVIDER
from tools.vector_db import CodeVectorDB
from langchain_community.chat_models import ChatAnthropic
from langchain_openai import ChatOpenAI
from config.settings import ANTHROPIC_API_KEY, OPENAI_API_KEY, ANTHROPIC_MODEL, OPENAI_MODEL

logger = logging.getLogger(__name__)

class TestGeneratorInput(BaseModel):
    file_path: str = Field(..., description="Path to the file to generate tests for")
    test_framework: Optional[str] = Field(None, description="Test framework to use (e.g., pytest, junit)")
    output_path: Optional[str] = Field(None, description="Path to save the generated tests")

class TestGeneratorTool(BaseTool):
    name = "test_generator"
    description = "Generates test cases for code files"
    args_schema = TestGeneratorInput
    project_path: Path = PROJECT_PATH
    vector_db: CodeVectorDB = None
    llm: Any = None
    
    def __init__(self):
        super().__init__()
        self.project_path = PROJECT_PATH
        self.vector_db = CodeVectorDB()
          # Initialize LLM based on configuration
        if LLM_PROVIDER.lower() == "anthropic":
            self.llm = ChatAnthropic(
                model=ANTHROPIC_MODEL,
                anthropic_api_key=ANTHROPIC_API_KEY,
                temperature=0.2
            )
        else:
            # Remove proxies parameter as it's no longer supported in newer versions
            self.llm = ChatOpenAI(
                model=OPENAI_MODEL,
                openai_api_key=OPENAI_API_KEY,
                temperature=0.2
            )
    
    def _run(self, file_path: str, test_framework: Optional[str] = None,
             output_path: Optional[str] = None) -> Dict[str, Any]:
        """Generate test cases for a code file."""
        if not file_path:
            return {"error": "File path is required"}
        
        full_path = self.project_path / file_path
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        try:
            # Read file content
            file_content = full_path.read_text(encoding='utf-8')
            
            # Determine file type and appropriate test framework
            file_type = full_path.suffix
            if not test_framework:
                test_framework = self._determine_test_framework(file_type)
            
            # Get similar code and existing tests for context
            context = self._get_context(file_path, file_type)
            
            # Generate tests using LLM
            tests = self._generate_tests(file_content, file_path, file_type, test_framework, context)
            
            # Save tests if output path is provided
            if output_path:
                self._save_tests(tests, output_path)
                return {
                    "success": True,
                    "file_path": file_path,
                    "test_framework": test_framework,
                    "output_path": output_path,
                    "tests": tests
                }
            else:
                return {
                    "success": True,
                    "file_path": file_path,
                    "test_framework": test_framework,
                    "tests": tests
                }
        except Exception as e:
            logger.error(f"Error generating tests for {file_path}: {str(e)}")
            return {"error": f"Error generating tests: {str(e)}"}
    
    def _determine_test_framework(self, file_type: str) -> str:
        """Determine appropriate test framework based on file type."""
        if file_type == '.py':
            # Check if pytest is used in the project
            if list(self.project_path.glob("**/pytest.ini")) or list(self.project_path.glob("**/conftest.py")):
                return "pytest"
            else:
                return "unittest"
        elif file_type in ['.js', '.ts', '.jsx', '.tsx']:
            # Check for Jest, Mocha, or other JS test frameworks
            package_json = self.project_path / "package.json"
            if package_json.exists():
                content = package_json.read_text()
                if "jest" in content:
                    return "jest"
                elif "mocha" in content:
                    return "mocha"
            return "jest"  # Default to Jest
        elif file_type == '.java':
            return "junit"
        elif file_type in ['.cs', '.vb']:
            return "xunit"
        else:
            return "generic"
    
    def _get_context(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Get context for test generation, including similar code and existing tests."""
        # Ensure vector database is initialized
        if not hasattr(self.vector_db, 'vector_store') or self.vector_db.vector_store is None:
            self.vector_db.embed_project()
        
        # Get file name without extension
        file_name = Path(file_path).stem
        
        # Search for similar code
        similar_code = self.vector_db.query_codebase(f"code similar to {file_path}", 3)
        
        # Search for existing tests
        test_file_patterns = {
            '.py': [f"test_{file_name}.py", f"{file_name}_test.py"],
            '.js': [f"{file_name}.test.js", f"{file_name}.spec.js"],
            '.ts': [f"{file_name}.test.ts", f"{file_name}.spec.ts"],
            '.java': [f"{file_name}Test.java", f"Test{file_name}.java"],
            '.cs': [f"{file_name}Tests.cs", f"Test{file_name}.cs"]
        }
        
        existing_tests = []
        patterns = test_file_patterns.get(file_type, [f"test_{file_name}.*", f"{file_name}_test.*"])
        
        for pattern in patterns:
            for test_file in self.project_path.glob(f"**/{pattern}"):
                try:
                    content = test_file.read_text(encoding='utf-8')
                    existing_tests.append({
                        "path": str(test_file.relative_to(self.project_path)),
                        "content": content
                    })
                except Exception as e:
                    logger.warning(f"Could not read test file {test_file}: {str(e)}")
        
        return {
            "similar_code": similar_code,
            "existing_tests": existing_tests
        }
    
    def _generate_tests(self, file_content: str, file_path: str, file_type: str,
                        test_framework: str, context: Dict[str, Any]) -> str:
        """Generate test cases using LLM."""
        # Create prompt for test generation
        prompt = self._create_test_prompt(file_content, file_path, file_type, test_framework, context)
        
        # Generate tests using LLM
        from langchain.schema import HumanMessage, SystemMessage
        
        messages = [
            SystemMessage(content="""You are an expert test engineer who writes high-quality, comprehensive test cases.
            Generate test cases that cover all functionality, edge cases, and error conditions.
            Follow best practices for the specified test framework.
            Include comments explaining the purpose of each test.
            """),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        # Extract code blocks from response
        import re
        code_pattern = r"```(?:\w+)?\n([\s\S]*?)\n```"
        code_matches = re.findall(code_pattern, response.content)
        
        if code_matches:
            return code_matches[0]
        else:
            # If no code block found, return the whole response
            return response.content
    
    def _create_test_prompt(self, file_content: str, file_path: str, file_type: str,
                          test_framework: str, context: Dict[str, Any]) -> str:
        """Create prompt for test generation."""
        prompt = f"""I need to generate tests for the following code file:

File path: {file_path}
File type: {file_type}
Test framework to use: {test_framework}

Here is the content of the file:

```
{file_content}
```

"""
        
        # Add context about existing tests if available
        if context["existing_tests"]:
            prompt += "\nHere are some existing tests in the project that might be helpful:\n\n"
            for test in context["existing_tests"][:2]:  # Limit to 2 test files to avoid token limits
                prompt += f"Test file: {test['path']}\n```\n{test['content']}\n```\n\n"
        
        # Add context about similar code if available
        if context["similar_code"]:
            prompt += "\nHere are some similar code files in the project:\n\n"
            for code in context["similar_code"][:2]:  # Limit to 2 similar files
                prompt += f"File: {code['source']}\n```\n{code['content']}\n```\n\n"
        
        # Add specific instructions based on test framework
        if test_framework == "pytest":
            prompt += """
Please generate pytest tests for this file. Include:
- Proper imports and fixtures
- Test functions that start with 'test_'
- Use of pytest assertions
- Mocking where appropriate
- Edge case testing
- Parametrized tests where applicable
"""
        elif test_framework == "unittest":
            prompt += """
Please generate unittest tests for this file. Include:
- A TestCase class that inherits from unittest.TestCase
- Test methods that start with 'test_'
- Proper use of setUp and tearDown methods if needed
- Appropriate assertions
- Edge case testing
"""
        elif test_framework == "jest":
            prompt += """
Please generate Jest tests for this file. Include:
- Proper describe and it blocks
- Use of expect assertions
- Mocking where appropriate
- Edge case testing
- Before/after hooks if needed
"""
        
        prompt += "\nPlease provide the complete test file that I can use directly without modifications."
        
        return prompt
    
    def _save_tests(self, tests: str, output_path: str) -> None:
        """Save generated tests to a file."""
        full_path = self.project_path / output_path
        
        # Create directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write tests to file
        full_path.write_text(tests, encoding='utf-8')
        logger.info(f"Tests saved to {output_path}")
