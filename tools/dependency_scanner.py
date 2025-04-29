import os
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from config.settings import REPO_LOCAL_PATH

logger = logging.getLogger(__name__)

class DependencyScannerInput(BaseModel):
    project_path: Path = Field(default=str(REPO_LOCAL_PATH), description="Path to the project directory")

class DependencyScanner(BaseTool):
    name: str = "dependency_scanner"
    description: str = "Scans a project for dependencies and identifies upgrade candidates"
    args_schema = DependencyScannerInput
    
    def _run(self, project_path: Path = Path(REPO_LOCAL_PATH)) -> Dict[str, Any]:
        """Run the dependency scanner."""
       
        project_path = Path(REPO_LOCAL_PATH) # Path(project_path)
        if not project_path.exists():
            return {"error": f"Project path {project_path} does not exist"}
        
        logger.info(f"Scanning dependencies in {project_path}")
        
        # Detect project type and dependencies
        project_type, dependency_files = self._detect_project_type(project_path)
        
        if not project_type:
            return {"error": "Could not determine project type"}
        
        # Parse dependencies based on project type
        dependencies = self._parse_dependencies(project_type, dependency_files)
        
        # Check for upgrade candidates
        upgrade_candidates = self._find_upgrade_candidates(project_type, dependencies)
        
        return {
            "project_type": project_type,
            "dependency_files": [str(f.relative_to(project_path)) for f in dependency_files],
            "dependencies": dependencies,
            "upgrade_candidates": upgrade_candidates
        }
    
    def _detect_project_type(self, project_path: Path) -> Tuple[Optional[str], List[Path]]:
        """Detect the type of project and find dependency files."""
        dependency_files = []
        
        # Check for Python project
        requirements_txt = list(project_path.glob("**/requirements.txt"))
        setup_py = list(project_path.glob("**/setup.py"))
        pyproject_toml = list(project_path.glob("**/pyproject.toml"))
        
        if requirements_txt or setup_py or pyproject_toml:
            dependency_files.extend(requirements_txt)
            dependency_files.extend(setup_py)
            dependency_files.extend(pyproject_toml)
            return "python", dependency_files
        
        # Check for Node.js project
        package_json = list(project_path.glob("**/package.json"))
        if package_json:
            dependency_files.extend(package_json)
            return "nodejs", dependency_files
        
        # Check for Java/Maven project
        pom_xml = list(project_path.glob("**/pom.xml"))
        if pom_xml:
            dependency_files.extend(pom_xml)
            return "maven", dependency_files
        
        # Check for Gradle project
        build_gradle = list(project_path.glob("**/build.gradle")) + list(project_path.glob("**/build.gradle.kts"))
        if build_gradle:
            dependency_files.extend(build_gradle)
            return "gradle", dependency_files
        
        # Check for .NET project
        csproj_files = list(project_path.glob("**/*.csproj"))
        if csproj_files:
            dependency_files.extend(csproj_files)
            return "dotnet", dependency_files
        
        return None, []
    
    def _parse_dependencies(self, project_type: str, dependency_files: List[Path]) -> List[Dict[str, str]]:
        """Parse dependencies based on project type."""
        dependencies = []
        
        for file_path in dependency_files:
            if project_type == "python":
                if file_path.name == "requirements.txt":
                    dependencies.extend(self._parse_requirements_txt(file_path))
                # Add other Python dependency file parsers as needed
            
            elif project_type == "nodejs":
                if file_path.name == "package.json":
                    dependencies.extend(self._parse_package_json(file_path))
            
            elif project_type == "maven":
                if file_path.name == "pom.xml":
                    dependencies.extend(self._parse_pom_xml(file_path))
            
            # Add other project type parsers as needed
        
        return dependencies
    
    def _parse_requirements_txt(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse Python requirements.txt file."""
        dependencies = []
        try:
            content = file_path.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Handle different formats
                if '==' in line:
                    name, version = line.split('==', 1)
                    dependencies.append({
                        "name": name.strip(),
                        "version": version.strip(),
                        "constraint": "==",
                        "file": str(file_path)
                    })
                elif '>=' in line:
                    name, version = line.split('>=', 1)
                    dependencies.append({
                        "name": name.strip(),
                        "version": version.strip(),
                        "constraint": ">=",
                        "file": str(file_path)
                    })
                # Add other formats as needed
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {str(e)}")
        
        return dependencies
    
    def _parse_package_json(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse Node.js package.json file."""
        dependencies = []
        try:
            content = json.loads(file_path.read_text())
            
            # Parse dependencies
            for dep_type in ["dependencies", "devDependencies"]:
                if dep_type in content:
                    for name, version in content[dep_type].items():
                        # Handle version formats
                        constraint = "^"  # Default
                        clean_version = version
                        
                        if version.startswith("^"):
                            constraint = "^"
                            clean_version = version[1:]
                        elif version.startswith("~"):
                            constraint = "~"
                            clean_version = version[1:]
                        
                        dependencies.append({
                            "name": name,
                            "version": clean_version,
                            "constraint": constraint,
                            "type": dep_type,
                            "file": str(file_path)
                        })
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {str(e)}")
        
        return dependencies
    
    def _parse_pom_xml(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse Maven pom.xml file."""
        dependencies = []
        try:
            # Simple regex-based parsing for demonstration
            content = file_path.read_text()
            
            # Find dependencies
            dep_pattern = r"<dependency>[\s\S]*?<groupId>(.*?)</groupId>[\s\S]*?<artifactId>(.*?)</artifactId>[\s\S]*?<version>(.*?)</version>[\s\S]*?</dependency>"
            matches = re.findall(dep_pattern, content)
            
            for group_id, artifact_id, version in matches:
                dependencies.append({
                    "name": f"{group_id}:{artifact_id}",
                    "group_id": group_id,
                    "artifact_id": artifact_id,
                    "version": version,
                    "file": str(file_path)
                })
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {str(e)}")
        
        return dependencies
    
    def _find_upgrade_candidates(self, project_type: str, dependencies: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Find upgrade candidates for the dependencies."""
        upgrade_candidates = []
        
        for dep in dependencies:
            if project_type == "python":
                candidates = self._check_python_upgrade(dep)
                if candidates:
                    upgrade_candidates.append(candidates)
            
            elif project_type == "nodejs":
                candidates = self._check_nodejs_upgrade(dep)
                if candidates:
                    upgrade_candidates.append(candidates)
            
            elif project_type == "maven":
                candidates = self._check_maven_upgrade(dep)
                if candidates:
                    upgrade_candidates.append(candidates)
            
            # Add other project type checkers as needed
        
        return upgrade_candidates
    
    def _check_python_upgrade(self, dependency: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Check for Python package upgrades using pip."""
        try:
            package_name = dependency["name"]
            current_version = dependency["version"]
            
            # Run pip to get latest version
            result = subprocess.run(
                ["pip", "index", "versions", package_name],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                # Parse the output to find the latest version
                output = result.stdout
                available_versions = re.findall(r"Available versions: (.*)", output)
                
                if available_versions:
                    versions = available_versions[0].split(", ")
                    latest_version = versions[0]  # First one is usually the latest
                    
                    if latest_version != current_version:
                        return {
                            "name": package_name,
                            "current_version": current_version,
                            "latest_version": latest_version,
                            "file": dependency["file"]
                        }
        except Exception as e:
            logger.error(f"Error checking upgrade for {dependency['name']}: {str(e)}")
        
        return None
    
    def _check_nodejs_upgrade(self, dependency: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Check for Node.js package upgrades using npm."""
        try:
            package_name = dependency["name"]
            current_version = dependency["version"]
            
            # Run npm to get latest version
            result = subprocess.run(
                ["npm", "view", package_name, "version"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                latest_version = result.stdout.strip()
                
                if latest_version != current_version:
                    return {
                        "name": package_name,
                        "current_version": current_version,
                        "latest_version": latest_version,
                        "type": dependency.get("type", "dependencies"),
                        "file": dependency["file"]
                    }
        except Exception as e:
            logger.error(f"Error checking upgrade for {dependency['name']}: {str(e)}")
        
        return None
    
    def _check_maven_upgrade(self, dependency: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Check for Maven package upgrades using Maven API."""
        try:
            group_id = dependency["group_id"]
            artifact_id = dependency["artifact_id"]
            current_version = dependency["version"]
            
            # Use Maven Central API to get latest version
            # This is a simplified example - in practice, you might want to use a proper Maven API client
            import requests
            url = f"https://search.maven.org/solrsearch/select?q=g:{group_id}+AND+a:{artifact_id}&rows=20&wt=json"
            
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data["response"]["numFound"] > 0:
                    docs = data["response"]["docs"]
                    latest_version = docs[0]["latestVersion"]
                    
                    if latest_version != current_version:
                        return {
                            "name": f"{group_id}:{artifact_id}",
                            "group_id": group_id,
                            "artifact_id": artifact_id,
                            "current_version": current_version,
                            "latest_version": latest_version,
                            "file": dependency["file"]
                        }
        except Exception as e:
            logger.error(f"Error checking upgrade for {dependency['name']}: {str(e)}")
        
        return None
