import os
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from config.settings import REPO_LOCAL_PATH

logger = logging.getLogger(__name__)

class CompilationInput(BaseModel):
    operation: str = Field(..., description="Operation to perform: compile or test")
    test_files: Optional[List[str]] = Field(None, description="List of test files to run")
    test_command: Optional[str] = Field(None, description="Custom test command to run")
    build_command: Optional[str] = Field(None, description="Custom build command to run")

class CompilationTool(BaseTool):
    name = "compilation"
    description = "Compiles the project and runs tests"
    args_schema = CompilationInput
    project_path = REPO_LOCAL_PATH
    
    
    def __init__(self):
        super().__init__()
        self.project_path = REPO_LOCAL_PATH
    
    def _run(self, operation: str, test_files: Optional[List[str]] = None,
             test_command: Optional[str] = None, build_command: Optional[str] = None) -> Dict[str, Any]:
        """Run compilation or test operations."""
        if operation == "compile":
            return self._compile_project(build_command)
        elif operation == "test":
            return self._run_tests(test_files, test_command)
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    def _compile_project(self, build_command: Optional[str] = None) -> Dict[str, Any]:
        """Compile the project."""
        try:
            # Detect project type and run appropriate build command
            if build_command:
                # Use custom build command if provided
                return self._run_command(build_command)
            else:
                # Auto-detect project type and use appropriate build command
                project_type = self._detect_project_type()
                
                if project_type == "python":
                    # For Python, check syntax
                    return self._check_python_syntax()
                elif project_type == "nodejs":
                    # For Node.js, run npm build
                    return self._run_command("npm run build")
                elif project_type == "maven":
                    # For Maven, run mvn compile
                    return self._run_command("mvn compile")
                elif project_type == "gradle":
                    # For Gradle, run gradle build
                    return self._run_command("./gradlew build -x test")
                elif project_type == "dotnet":
                    # For .NET, run dotnet build
                    return self._run_command("dotnet build")
                else:
                    return {"error": f"Could not determine project type for compilation"}
        except Exception as e:
            logger.error(f"Error compiling project: {str(e)}")
            return {"error": f"Error compiling project: {str(e)}"}
    
    def _run_tests(self, test_files: Optional[List[str]] = None,
                  test_command: Optional[str] = None) -> Dict[str, Any]:
        """Run project tests."""
        try:
            # Use custom test command if provided
            if test_command:
                return self._run_command(test_command)
            
            # Auto-detect project type and use appropriate test command
            project_type = self._detect_project_type()
            
            if project_type == "python":
                # For Python, run pytest or unittest
                if Path(self.project_path / "pytest.ini").exists() or list(self.project_path.glob("**/test_*.py")):
                    if test_files:
                        return self._run_command(f"pytest {' '.join(test_files)}")
                    else:
                        return self._run_command("pytest")
                else:
                    if test_files:
                        return self._run_command(f"python -m unittest {' '.join(test_files)}")
                    else:
                        return self._run_command("python -m unittest discover")
            
            elif project_type == "nodejs":
                # For Node.js, run npm test
                return self._run_command("npm test")
            
            elif project_type == "maven":
                # For Maven, run mvn test
                if test_files:
                    test_classes = " ".join([f"-Dtest={Path(f).stem}" for f in test_files])
                    return self._run_command(f"mvn test {test_classes}")
                else:
                    return self._run_command("mvn test")
            
            elif project_type == "gradle":
                # For Gradle, run gradle test
                return self._run_command("./gradlew test")
            
            elif project_type == "dotnet":
                # For .NET, run dotnet test
                if test_files:
                    return self._run_command(f"dotnet test {' '.join(test_files)}")
                else:
                    return self._run_command("dotnet test")
            
            else:
                return {"error": f"Could not determine project type for testing"}
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}")
            return {"error": f"Error running tests: {str(e)}"}
    
    def _detect_project_type(self) -> Optional[str]:
        """Detect the type of project."""
        # Check for Python project
        if list(self.project_path.glob("**/requirements.txt")) or \
           list(self.project_path.glob("**/setup.py")) or \
           list(self.project_path.glob("**/pyproject.toml")):
            return "python"
        
        # Check for Node.js project
        if list(self.project_path.glob("**/package.json")):
            return "nodejs"
        
        # Check for Maven project
        if list(self.project_path.glob("**/pom.xml")):
            return "maven"
        
        # Check for Gradle project
        if list(self.project_path.glob("**/build.gradle")) or \
           list(self.project_path.glob("**/build.gradle.kts")):
            return "gradle"
        
        # Check for .NET project
        if list(self.project_path.glob("**/*.csproj")) or \
           list(self.project_path.glob("**/*.sln")):
            return "dotnet"
        
        return None
    
    def _check_python_syntax(self) -> Dict[str, Any]:
        """Check Python syntax."""
        python_files = []
        for ext in [".py"]:
            python_files.extend(list(self.project_path.glob(f"**/*{ext}")))
        
        # Filter out files in directories that should be ignored
        ignored_dirs = ['venv', '.git', '.vscode', '__pycache__', 'node_modules']
        python_files = [
            f for f in python_files 
            if not any(ignored_dir in str(f) for ignored_dir in ignored_dirs)
        ]
        
        errors = []
        for file_path in python_files:
            try:
                # Check syntax using py_compile
                result = subprocess.run(
                    ["python", "-m", "py_compile", str(file_path)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    errors.append({
                        "file": str(file_path.relative_to(self.project_path)),
                        "error": result.stderr.strip()
                    })
            except Exception as e:
                errors.append({
                    "file": str(file_path.relative_to(self.project_path)),
                    "error": str(e)
                })
        
        if errors:
            return {
                "success": False,
                "errors": errors,
                "message": f"Found {len(errors)} files with syntax errors"
            }
        else:
            return {
                "success": True,
                "message": f"All {len(python_files)} Python files passed syntax check"
            }
    
    def _run_command(self, command: str) -> Dict[str, Any]:
        """Run a shell command in the project directory."""
        try:
            logger.info(f"Running command: {command}")
            
            # Run the command
            process = subprocess.run(
                command,
                shell=True,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Process the result
            if process.returncode == 0:
                return {
                    "success": True,
                    "command": command,
                    "output": process.stdout,
                    "message": f"Command executed successfully"
                }
            else:
                return {
                    "success": False,
                    "command": command,
                    "output": process.stdout,
                    "error": process.stderr,
                    "message": f"Command failed with exit code {process.returncode}"
                }
        except Exception as e:
            logger.error(f"Error running command '{command}': {str(e)}")
            return {
                "success": False,
                "command": command,
                "error": str(e),
                "message": f"Error executing command"
            }
