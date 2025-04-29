import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

import git
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from config.settings import REPO_LOCAL_PATH, GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_EMAIL

logger = logging.getLogger(__name__)

class GitOperationInput(BaseModel):
    operation: str = Field(..., description="Git operation to perform: create_branch, commit, push, or create_pr")
    branch_name: Optional[str] = Field(None, description="Branch name for create_branch, push, or create_pr")
    commit_message: Optional[str] = Field(None, description="Commit message for commit operation")
    pr_title: Optional[str] = Field(None, description="Pull request title for create_pr operation")
    pr_description: Optional[str] = Field(None, description="Pull request description for create_pr operation")
    files: Optional[List[str]] = Field(None, description="List of files to add for commit operation")
    base_branch: Optional[str] = Field("main", description="Base branch for create_pr operation")

class GitOperationsTool(BaseTool):
    name = "git_operations"
    description = "Performs Git operations like creating branches, committing changes, pushing to remote, and creating pull requests"
    args_schema = GitOperationInput
    repo_path:  Path = None
    repo: Optional[git.Repo] = None
    
    def __init__(self):
        super().__init__()
        self.repo_path = REPO_LOCAL_PATH
        try:
            self.repo = git.Repo(self.repo_path)
            # Configure git user
            if GITHUB_USERNAME and GITHUB_EMAIL:
                self.repo.git.config("user.name", GITHUB_USERNAME)
                self.repo.git.config("user.email", GITHUB_EMAIL)
        except git.exc.InvalidGitRepositoryError:
            logger.error(f"{self.repo_path} is not a valid Git repository")
            self.repo = None
    
    def _run(self, operation: str, branch_name: Optional[str] = None, 
             commit_message: Optional[str] = None, pr_title: Optional[str] = None, 
             pr_description: Optional[str] = None, files: Optional[List[str]] = None,
             base_branch: Optional[str] = "main") -> Dict[str, Any]:
        """Run Git operations."""
        if not self.repo:
            return {"error": f"{self.repo_path} is not a valid Git repository"}
        
        if operation == "create_branch":
            return self._create_branch(branch_name)
        elif operation == "commit":
            return self._commit_changes(commit_message, files)
        elif operation == "push":
            return self._push_changes(branch_name)
        elif operation == "create_pr":
            return self._create_pull_request(branch_name, base_branch, pr_title, pr_description)
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    def _create_branch(self, branch_name: str) -> Dict[str, Any]:
        """Create a new Git branch."""
        if not branch_name:
            return {"error": "Branch name is required"}
        
        try:
            # Check if branch already exists
            if branch_name in [ref.name.split('/')[-1] for ref in self.repo.refs]:
                # Checkout existing branch
                self.repo.git.checkout(branch_name)
                return {"success": True, "message": f"Switched to existing branch: {branch_name}"}
            
            # Create and checkout new branch
            self.repo.git.checkout('-b', branch_name)
            return {"success": True, "message": f"Created and switched to new branch: {branch_name}"}
        except git.GitCommandError as e:
            logger.error(f"Git error creating branch {branch_name}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _commit_changes(self, commit_message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Commit changes to Git repository."""
        if not commit_message:
            return {"error": "Commit message is required"}
        
        try:
            # Add specific files or all changes
            if files:
                for file in files:
                    file_path = Path(self.repo_path) / file
                    if file_path.exists():
                        self.repo.git.add(file)
                    else:
                        logger.warning(f"File not found: {file}")
            else:
                self.repo.git.add('.')
            
            # Check if there are changes to commit
            if not self.repo.git.diff('--staged'):
                return {"success": False, "message": "No changes to commit"}
            
            # Commit changes
            self.repo.git.commit('-m', commit_message)
            return {"success": True, "message": f"Changes committed with message: {commit_message}"}
        except git.GitCommandError as e:
            logger.error(f"Git error committing changes: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _push_changes(self, branch_name: Optional[str] = None) -> Dict[str, Any]:
        """Push changes to remote repository."""
        try:
            if branch_name:
                self.repo.git.push('--set-upstream', 'origin', branch_name)
            else:
                self.repo.git.push()
            
            current_branch = self.repo.active_branch.name
            return {"success": True, "message": f"Changes pushed to {current_branch}"}
        except git.GitCommandError as e:
            logger.error(f"Git error pushing changes: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_pull_request(self, branch_name: str, base_branch: str, 
                           pr_title: str, pr_description: str) -> Dict[str, Any]:
        """Create a pull request using GitHub API."""
        if not all([branch_name, pr_title, GITHUB_TOKEN]):
            missing = []
            if not branch_name:
                missing.append("branch_name")
            if not pr_title:
                missing.append("pr_title")
            if not GITHUB_TOKEN:
                missing.append("GITHUB_TOKEN")
            
            return {"error": f"Missing required parameters: {', '.join(missing)}"}
        
        try:
            import requests
            
            # Get repository info from remote URL
            remote_url = self.repo.remotes.origin.url
            repo_info = self._extract_repo_info(remote_url)
            
            if not repo_info:
                return {"error": f"Could not extract repository info from {remote_url}"}
            
            # Create pull request
            url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/pulls"
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            data = {
                "title": pr_title,
                "body": pr_description,
                "head": branch_name,
                "base": base_branch
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 201:
                pr_data = response.json()
                return {
                    "success": True,
                    "message": f"Pull request created: {pr_data['html_url']}",
                    "pr_url": pr_data['html_url'],
                    "pr_number": pr_data['number']
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create PR: {response.status_code} - {response.text}"
                }
        except Exception as e:
            logger.error(f"Error creating pull request: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _extract_repo_info(self, remote_url: str) -> Optional[Dict[str, str]]:
        """Extract owner and repo name from remote URL."""
        # Handle different URL formats
        if remote_url.startswith("https://github.com/"):
            parts = remote_url.replace("https://github.com/", "").replace(".git", "").split("/")
            if len(parts) >= 2:
                return {"owner": parts[0], "repo": parts[1]}
        
        elif remote_url.startswith("git@github.com:"):
            parts = remote_url.replace("git@github.com:", "").replace(".git", "").split("/")
            if len(parts) >= 2:
                return {"owner": parts[0], "repo": parts[1]}
        
        return None
