import logging
import sys
from pathlib import Path

def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "upgrade_agent.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Return logger
    return logging.getLogger("upgrade_agent")

logger = setup_logging()
