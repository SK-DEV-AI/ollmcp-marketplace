"""OAuth authentication providers for Smithery and other MCP servers.

This module provides a simple wrapper around the MCP library's OAuthClientProvider
to handle Smithery server authentication.
"""

import json
import asyncio
from typing import Optional
from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import OAuthClientMetadata, OAuthToken
from ..utils.constants import DEFAULT_CONFIG_DIR


class SimpleTokenStorage:
    """Simple token storage for MCP OAuth provider."""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.server_id = self._extract_server_id(server_url)

    async def get_tokens(self) -> OAuthToken | None:
        """Get stored tokens."""
        token_file = self._get_token_file_path()
        if not token_file.exists():
            return None

        try:
            with open(token_file, 'r') as f:
                data = json.load(f)
            return OAuthToken(**data.get("tokens", {}))
        except Exception:
            return None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        """Store tokens."""
        import os
        os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)

        token_file = self._get_token_file_path()
        token_data = {
            "server_url": self.server_url,
            "tokens": tokens.model_dump()
        }

        with open(token_file, 'w') as f:
            json.dump(token_data, f, indent=2)

    async def get_client_info(self):
        """Get stored client information."""
        return None

    async def set_client_info(self, client_info) -> None:
        """Store client information."""
        # Not needed for simple implementation
        pass

    def _extract_server_id(self, server_url: str) -> str:
        "" "Extract unique server identifier from URL." ""
        if "smithery.ai" in server_url:
            parts = server_url.split("/")
            for i, part in enumerate(parts):
                if part.startswith("@"):
                    server_id = "/".join(parts[i:i+2])
                    return server_id.replace("/", "_")

        # Fallback to URL hash
        return str(hash(server_url) % 1000000).replace('-', '')

    def _get_token_file_path(self):
        """Get token file path."""
        from pathlib import Path
        return Path(DEFAULT_CONFIG_DIR) / f"oauth_tokens_{self.server_id}.json"


class OAuthProviderFactory:
    """Factory class for creating OAuth providers for different server types."""

    @staticmethod
    def create_provider(server_url: str, server_type: str = "smithery") -> Optional[OAuthClientProvider]:
        """Create an OAuth provider for the given server.

        Args:
            server_url: The server URL requiring OAuth
            server_type: The type of server (e.g., 'smithery')

        Returns:
            An OAuth provider instance or None if not supported
        """
        if server_type == "smithery" or "smithery.ai" in server_url:
            return SmitheryOAuthProvider(server_url)
        return None


class SmitheryOAuthProvider(OAuthClientProvider):
    """OAuth provider for Smithery MCP servers using MCP library's implementation."""

    def __init__(self, server_url: str, client_name: str = "MCP Client for Ollama"):
        """Initialize Smithery OAuth provider."""
        self.server_url = server_url

        # Set up client metadata
        client_metadata = OAuthClientMetadata(
            client_name=client_name,
            client_uri="https://github.com/SK-DEV-AI/ollmcp-marketplace",
            redirect_uris=["http://localhost:8080/oauth/callback"],
            scope="read write",
            grant_types=["authorization_code"],
            response_types=["code"]
        )

        # Set up storage
        storage = SimpleTokenStorage(server_url)

        # Set up handlers (these will be used for headless mode)
        async def redirect_handler(url: str) -> None:
            print(f"\n🔗 ====== OAUTH AUTHORIZATION REQUIRED ======")
            print(f"Please copy and open this URL in your browser:")
            print(f"{url}")
            print(f"\nComplete the authorization, then copy the authorization code")
            print(f"from the redirect URL and enter it when prompted.")
            print(f"=========================================\n")

        async def callback_handler():
            # In headless mode, we need to prompt for the authorization code
            auth_code = input("Enter authorization code: ").strip()
            return auth_code, None

        # Initialize the MCP OAuth provider
        super().__init__(
            server_url=server_url,
            client_metadata=client_metadata,
            storage=storage,
            redirect_handler=redirect_handler,
            callback_handler=callback_handler,
            timeout=600.0  # 10 minute timeout for interactive auth
        )
