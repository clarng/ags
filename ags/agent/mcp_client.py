import json
import subprocess
import sys
from typing import Dict, List, Optional
import os


DEFAULT_CONFIG_PATH = "/Library/Application Support/Claude/claude_desktop_config.json"


class MCPClient:
    def __init__(self, config_path: str = None):
        """Initialize the MCP client with configuration from the specified path."""
        if config_path is None:
            home = os.getenv('HOME','/')
            config_path = home + os.getenv('MCP_CONFIG_PATH', DEFAULT_CONFIG_PATH)
        self.config = self._load_config(config_path)
        self.filesystem_server = self._get_filesystem_server()

    def _load_config(self, config_path: str) -> Dict:
        """Load the MCP configuration from the specified JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file not found at {config_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in configuration file {config_path}")
            sys.exit(1)

    def _get_filesystem_server(self) -> Dict:
        """Get the filesystem server configuration."""
        if 'mcpServers' not in self.config or 'filesystem' not in self.config['mcpServers']:
            print("Error: Filesystem server configuration not found")
            sys.exit(1)
        return self.config['mcpServers']['filesystem']

    def run_filesystem_command(self, command: str) -> Optional[str]:
        """Run a command through the filesystem server."""
        try:
            # Construct the full command with Docker arguments
            docker_args = self.filesystem_server['args']
            full_command = [self.filesystem_server['command']] + docker_args

            # Run the command and capture output
            result = subprocess.run(
                full_command,
                input=command.encode(),
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"Error: Command failed with return code {result.returncode}")
                print(f"Error output: {result.stderr}")
                return None

            return result.stdout.strip()

        except Exception as e:
            print(f"Error running command: {str(e)}")
            return None

def main():
    # Example usage
    client = MCPClient()
    
    # Example command to list files
    result = client.run_filesystem_command("ls")
    if result:
        print("Files in directory:")
        print(result)
    else:
        print("Failed to execute command")

if __name__ == "__main__":
    main() 