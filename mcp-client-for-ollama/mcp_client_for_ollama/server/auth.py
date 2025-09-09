"""Authentication providers for Smithery and other MCP servers.

This module provides authentication for MCP servers, focusing on Smithery's
Bearer token authentication for both registry and server endpoints.
"""

from typing import Optional, Dict, Any


class SmitheryAuthProvider:
    """Authentication provider for Smithery MCP servers.

    This class handles the specific authentication requirements for Smithery servers,
    which use Bearer tokens for both registry access and server connections.
    """

    def __init__(self, server_url: str, api_key: Optional[str] = None):
        """Initialize Smithery authentication provider.

        Args:
            server_url: The URL of the Smithery server
            api_key: Smithery API key if available
        """
        self.server_url = server_url
        self.api_key = api_key

    def get_auth_headers(self) -> Dict[str, Any]:
        """Get authentication headers for the server connection.

        Returns:
            Dictionary of headers to include in the request
        """
        headers = {}

        # For Smithery servers, use Bearer token authentication
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def has_credentials(self) -> bool:
        """Check if credentials are available."""
        return bool(self.api_key)


class AuthProviderFactory:
    """Factory class for creating authentication providers for different server types."""

    @staticmethod
    def create_provider(server_url: str, api_key: Optional[str] = None, server_type: str = "auto"):
        """Create an authentication provider for the given server.

        Args:
            server_url: The server URL requiring authentication
            api_key: API key to use for authentication
            server_type: The type of server or 'auto' to detect

        Returns:
            An authentication provider instance or None if not supported
        """
        # Auto-detect server type
        if server_type == "auto":
            if "smithery.ai" in server_url or server_url.startswith("@") and "/" in server_url:
                server_type = "smithery"

        if server_type == "smithery":
            return SmitheryAuthProvider(server_url, api_key)

        return None
