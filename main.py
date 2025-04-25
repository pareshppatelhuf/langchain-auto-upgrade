import argparse
import logging
import sys
from pathlib import Path

from config.logging_config import setup_logging
from agents.upgrade_agent import UpgradeAgent
from agents.test_agent import TestAgent
from utils.message_formatter import MessageFormatter, Role

logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Automated Dependency Upgrade Agent")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Initialize vector database command
    init_parser = subparsers.add_parser("init", help="Initialize vector database")
    init_parser.add_argument("--force", action="store_true", help="Force refresh of vector database")
    
    # Upgrade specific dependency command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade a specific dependency")
    upgrade_parser.add_argument("--dependency", help="Name of the dependency to upgrade")
    upgrade_parser.add_argument("--version", help="Target version to upgrade to")
    
    # Scan and upgrade all dependencies command
    scan_parser = subparsers.add_parser("scan", help="Scan and upgrade all dependencies")
    
    # Generate tests command
    test_parser = subparsers.add_parser("test", help="Generate or run tests")
    test_parser.add_argument("--file", help="Path to the file to generate tests for")
    test_parser.add_argument("--framework", help="Test framework to use")
    test_parser.add_argument("--output", help="Path to save generated tests")
    test_parser.add_argument("--run", action="store_true", help="Run tests instead of generating them")
    test_parser.add_argument("--test-files", nargs="+", help="List of test files to run")
    
    # Interactive mode command
    interactive_parser = subparsers.add_parser("interactive", help="Run in interactive mode")
    interactive_parser.add_argument("--agent", choices=["upgrade", "test"], default="upgrade", 
                                  help="Choose which agent to use in interactive mode")
    
    return parser.parse_args()

def run_interactive_mode(agent):
    """Run the agent in interactive mode."""
    print(MessageFormatter.format_message(Role.SYSTEM, "Starting interactive mode. Type 'exit' to quit."))
    
    while True:
        # Get user input
        user_input = input("> ")
        
        if user_input.lower() == "exit":
            print(MessageFormatter.format_message(Role.SYSTEM, "Exiting interactive mode."))
            break
        
        # Run the agent
        try:
            agent.run(user_input)
        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(MessageFormatter.format_message(Role.SYSTEM, error_message))
            logger.error(error_message)

def main():
    """Main entry point."""
    # Set up logging
    setup_logging()
    
    # Parse arguments
    args = parse_args()
    
    # Create the appropriate agent based on the command
    if args.command == "test" or (args.command == "interactive" and args.agent == "test"):
        agent = TestAgent()
    else:
        agent = UpgradeAgent()
    
    # Handle commands
    if args.command == "init":
        print(MessageFormatter.format_message(Role.SYSTEM, "Initializing vector database..."))
        agent.initialize_vector_db(force_refresh=args.force)
        print(MessageFormatter.format_message(Role.SYSTEM, "Vector database initialized successfully."))

    elif args.command == "scan":
        print(MessageFormatter.format_message(Role.SYSTEM, "Scanning all dependencies and finding upgrade candidate"))
        agent.scan_and_find_upgrade_candidate()

    elif args.command == "upgrade":
        print(MessageFormatter.format_message(Role.SYSTEM, f"Upgrading dependency: {args.dependency}"))
        agent.upgrade_dependency(args.dependency, args.version)
    

    
    elif args.command == "test":
        if args.run:
            if args.test_files:
                print(MessageFormatter.format_message(Role.SYSTEM, f"Running specific test files: {args.test_files}"))
                agent.run_tests(args.test_files)
            else:
                print(MessageFormatter.format_message(Role.SYSTEM, "Running all tests..."))
                agent.run_tests()
        else:
            if not args.file:
                print(MessageFormatter.format_message(Role.SYSTEM, "Error: --file is required when generating tests."))
                return
            
            print(MessageFormatter.format_message(Role.SYSTEM, f"Generating tests for: {args.file}"))
            agent.generate_tests_for_file(args.file, args.framework, args.output)
    
    elif args.command == "interactive":
        agent_type = "Test" if args.agent == "test" else "Upgrade"
        print(MessageFormatter.format_message(Role.SYSTEM, f"Starting interactive mode with {agent_type} Agent."))
        run_interactive_mode(agent)
    
    else:
        print(MessageFormatter.format_message(Role.SYSTEM, "No command specified. Use --help for available commands."))

if __name__ == "__main__":
    main()
