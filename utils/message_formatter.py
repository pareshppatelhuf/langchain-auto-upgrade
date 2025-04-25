from typing import Dict, Any, List
from enum import Enum
import re

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

class MessageFormatter:
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
        
        # Format the box with color
        box = f"""
┌───────────────────────────── {header} ─────────────────────────────┐
│                                                                    │
{MessageFormatter._wrap_content(content)}
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
"""
        return box
    
    @staticmethod
    def _wrap_content(content: str, max_width: int = 68) -> str:
        """Wrap content to fit within the box."""
        lines = content.split('\n')
        wrapped_lines = []
        
        for line in lines:
            if len(line) <= max_width:
                wrapped_lines.append(f"│ {line.ljust(max_width)} │")
            else:
                # Split long lines
                current_line = ""
                for word in line.split():
                    if len(current_line) + len(word) + 1 <= max_width:
                        current_line += " " + word if current_line else word
                    else:
                        wrapped_lines.append(f"│ {current_line.ljust(max_width)} │")
                        current_line = word
                if current_line:
                    wrapped_lines.append(f"│ {current_line.ljust(max_width)} │")
        
        return "\n".join(wrapped_lines)
    
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
