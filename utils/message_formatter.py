from typing import Dict, Any, List
from enum import Enum
import re
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

class MessageFormatter:
    console = Console(highlight=False)
    
    @staticmethod
    def format_message(role: Role, content: str) -> str:
        """Format a message with a colored box based on the role."""
        if role == Role.SYSTEM:
            color = "blue"
            emoji = "🤖"
        elif role == Role.USER:
            color = "green"
            emoji = "👤"
        elif role == Role.ASSISTANT:
            color = "purple"
            emoji = "🧠"
        elif role == Role.FUNCTION:
            color = "orange"
            emoji = "⚙️"
        else:
            color = "gray"
            emoji = "📝"
            
        header = f"{emoji} {role.upper()}"
        
        # Create a rich panel with proper styling
        panel = Panel(
            content,
            title=header,
            border_style=color,
            expand=False,
            padding=(1, 2)
        )
        
        # Convert to string representation
        with MessageFormatter.console.capture() as capture:
            MessageFormatter.console.print(panel)
        
        return capture.get()
    
    @staticmethod
    def format_code_block(code: str, language: str = "") -> str:
        """Format code in a markdown code block."""
        return f"```{language}\n{code}\n```"
    
    @staticmethod
    def extract_code_blocks(text: str) -> List[Dict[str, str]]:
        """Extract code blocks from text."""
        pattern = r"```(\w*)\n([\s\S]*?)\n```"
        matches = re.findall(pattern, text)
        
        code_blocks = []
        for language, code in matches:
            code_blocks.append({
                "language": language,
                "code": code
            })
        
        return code_blocks
