import json
import os
from typing import Dict, Any

from ..utils.constants import DEFAULT_CONFIG_DIR

MCP_HUB_CONFIG_FILE = "mcp.json"

class MCPHubConfigManager:
    """Manages the MCP servers configuration in a dedicated mcp.json file."""

    def __init__(self):
        self.config_path = os.path.join(DEFAULT_CONFIG_DIR, MCP_HUB_CONFIG_FILE)

    def _read_config(self) -> Dict[str, Any]:
        """Reads the mcp.json file and returns its content."""
        if not os.path.exists(self.config_path):
            return {"mcpServers": {}}

        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                if "mcpServers" not in data:
                    data["mcpServers"] = {}
                return data
        except (json.JSONDecodeError, IOError):
            return {"mcpServers": {}}

    def _write_config(self, data: Dict[str, Any]):
        """Writes the given data to the mcp.json file."""
        os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_servers(self) -> Dict[str, Any]:
        """Gets the dictionary of all configured servers."""
        config = self._read_config()
        return config.get("mcpServers", {})

    def add_server(self, server_name: str, server_config: Dict[str, Any]):
        """Adds a new server configuration."""
        config = self._read_config()
        config["mcpServers"][server_name] = server_config
        self._write_config(config)

    def remove_server(self, server_name: str):
        """Removes a server configuration."""
        config = self._read_config()
        if server_name in config["mcpServers"]:
            del config["mcpServers"][server_name]
            self._write_config(config)

    def get_config_path(self) -> str:
        """Returns the full path to the mcp.json file."""
        return self.config_path
