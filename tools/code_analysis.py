import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from config.settings import REPO_LOCAL_PATH
from tools.vector_db import CodeVectorDB

logger = logging.getLogger(__name__)

class CodeAnalysisInput(BaseModel):
    operation: str = Field(..., description="Operation to perform: analyze_file, modify_file, search_code, or get_file")
    file_path: Optional[str] = Field(None, description="Path to the file relative to project root")
    query: Optional[str] = Field(None, description="Query for searching code")
    new_content: Optional[str] = Field(None, description="New content for file modification")
    n_results: Optional[int] = Field(5, description="Number of results to return for search operation")

class CodeAnalysisTool(BaseTool):
    name: str = "code_analysis"
    description: str = "Analyzes and modifies code files, searches codebase for relevant code"
    args_schema = CodeAnalysisInput
    project_path: Path = None
    vector_db: CodeVectorDB = None
    
    def __init__(self):
        super().__init__()
        self.project_path = REPO_LOCAL_PATH
        self.vector_db = CodeVectorDB()
    
    def _run(self, operation: str, file_path: Optional[str] = None, 
             query: Optional[str] = None, new_content: Optional[str] = None,
             n_results: Optional[int] = 5) -> Dict[str, Any]:
        """Run code analysis operations."""
        if operation == "analyze_file":
            return self._analyze_file(file_path)
        elif operation == "modify_file":
            return self._modify_file(file_path, new_content)
        elif operation == "search_code":
            return self._search_code(query, n_results)
        elif operation == "get_file":
            return self._get_file(file_path)
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    def _analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a code file."""
        if not file_path:
            return {"error": "File path is required"}
        
        full_path = self.project_path / file_path
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        try:
            content = full_path.read_text(encoding='utf-8')
            
            # Basic file analysis
            file_info = {
                "file_path": file_path,
                "size_bytes": full_path.stat().st_size,
                "extension": full_path.suffix,
                "content": content,
                "line_count": len(content.splitlines())
            }
            
            # Add language-specific analysis
            if file_path.endswith('.py'):
                file_info.update(self._analyze_python_file(content))
            elif file_path.endswith('.js') or file_path.endswith('.ts'):
                file_info.update(self._analyze_js_file(content))
            elif file_path.endswith('.java'):
                file_info.update(self._analyze_java_file(content))
            
            return file_info
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            return {"error": f"Error analyzing file: {str(e)}"}
    
    def _analyze_python_file(self, content: str) -> Dict[str, Any]:
        """Analyze Python file."""
        import re
        
        # Find imports
        import_pattern = r'^import\s+(\w+)|^from\s+(\w+(?:\.\w+)*)\s+import'
        imports = set()
        
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            if match.group(1):
                imports.add(match.group(1))
            elif match.group(2):
                imports.add(match.group(2).split('.')[0])
        
        # Find class definitions
        class_pattern = r'class\s+(\w+)'
        classes = re.findall(class_pattern, content)
        
        # Find function definitions
        function_pattern = r'def\s+(\w+)'
        functions = re.findall(function_pattern, content)
        
        return {
            "language": "python",
            "imports": list(imports),
            "classes": classes,
            "functions": functions
        }
    
    def _analyze_js_file(self, content: str) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript file."""
        import re
        
        # Find imports
        import_pattern = r'(?:import|require)\s*\(?[\'"](.+?)[\'"]'
        imports = re.findall(import_pattern, content)
        
        # Find class definitions
        class_pattern = r'class\s+(\w+)'
        classes = re.findall(class_pattern, content)
        
        # Find function definitions
        function_pattern = r'(?:function|const|let|var)\s+(\w+)\s*\('
        functions = re.findall(function_pattern, content)
        
        return {
            "language": "javascript/typescript",
            "imports": imports,
            "classes": classes,
            "functions": functions
        }
    
    def _analyze_java_file(self, content: str) -> Dict[str, Any]:
        """Analyze Java file."""
        import re
        
        # Find imports
        import_pattern = r'import\s+(.+?);'
        imports = re.findall(import_pattern, content)
        
        # Find class definitions
        class_pattern = r'(?:public|private|protected)?\s*class\s+(\w+)'
        classes = re.findall(class_pattern, content)
        
        # Find method definitions
        method_pattern = r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\('
        methods = re.findall(method_pattern, content)
        
        return {
            "language": "java",
            "imports": imports,
            "classes": classes,
            "methods": methods
        }
    
    def _modify_file(self, file_path: str, new_content: str) -> Dict[str, Any]:
        """Modify a code file."""
        if not file_path or not new_content:
            missing = []
            if not file_path:
                missing.append("file_path")
            if not new_content:
                missing.append("new_content")
            
            return {"error": f"Missing required parameters: {', '.join(missing)}"}
        
        full_path = self.project_path / file_path
        
        try:
            # Create directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save original content for comparison
            original_content = ""
            if full_path.exists():
                original_content = full_path.read_text(encoding='utf-8')
            
            # Write new content
            full_path.write_text(new_content, encoding='utf-8')
            
            return {
                "success": True,
                "file_path": file_path,
                "message": "File modified successfully",
                "is_new_file": not original_content,
                "changed_lines": len(new_content.splitlines()) if not original_content else self._count_changed_lines(original_content, new_content)
            }
        except Exception as e:
            logger.error(f"Error modifying file {file_path}: {str(e)}")
            return {"error": f"Error modifying file: {str(e)}"}
    
    def _count_changed_lines(self, original: str, new: str) -> int:
        """Count the number of changed lines between original and new content."""
        original_lines = original.splitlines()
        new_lines = new.splitlines()
        
        # Use difflib for a more sophisticated diff
        import difflib
        diff = difflib.unified_diff(original_lines, new_lines, n=0)
        
        # Count changed lines
        changed_lines = 0
        for line in diff:
            if line.startswith('+') or line.startswith('-'):
                if not line.startswith('+++') and not line.startswith('---'):
                    changed_lines += 1
        
        return changed_lines
    
    def _search_code(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Search codebase for relevant code."""
        if not query:
            return {"error": "Query is required"}
        
        try:
            # Ensure vector database is initialized
            if not hasattr(self.vector_db, 'vector_store') or self.vector_db.vector_store is None:
                self.vector_db.embed_project()
            
            # Search for relevant code
            results = self.vector_db.query_codebase(query, n_results)
            
            return {
                "query": query,
                "results": results,
                "result_count": len(results)
            }
        except Exception as e:
            logger.error(f"Error searching code: {str(e)}")
            return {"error": f"Error searching code: {str(e)}"}
    
    def _get_file(self, file_path: str) -> Dict[str, Any]:
        """Get file content."""
        if not file_path:
            return {"error": "File path is required"}
        
        full_path = self.project_path / file_path
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        try:
            content = full_path.read_text(encoding='utf-8')
            
            return {
                "file_path": file_path,
                "content": content,
                "size_bytes": full_path.stat().st_size,
                "extension": full_path.suffix
            }
        except Exception as e:
            logger.error(f"Error getting file {file_path}: {str(e)}")
            return {"error": f"Error getting file: {str(e)}"}
