"""OAuth authentication providers for Smithery and other MCP servers.

This module implements OAuth client providers for MCP servers that require
OAuth flow authentication, particularly Smithery servers.
"""

import json
import os
from typing import Dict, Any, Optional
from mcp.client.auth import OAuthClientProvider, OAuthClientInformation, OAuthClientMetadata, OAuthTokens
from ..utils.constants import DEFAULT_CONFIG_DIR

class SmitheryOAuthProvider(OAuthClientProvider):
    """OAuth provider for Smithery MCP servers.

    This class implements the OAuthClientProvider interface specifically
    for Smithery servers that require OAuth authentication rather than
    direct Bearer tokens.
    """

    def __init__(self, server_url: str, client_name: str = "MCP Client for Ollama"):
        """Initialize the Smithery OAuth provider.

        Args:
            server_url: The URL of the Smithery server
            client_name: Name to display during OAuth callback
        """
        self.server_url = server_url
        self.client_name = client_name

        # Extract server identifier from URL for storage
        self.server_id = self._extract_server_id(server_url)

        # Load existing tokens if available
        self._tokens = self._load_stored_tokens()

    def redirect_url(self) -> str:
        """Get the OAuth callback URL for this provider.

        Returns:
            The redirect URL for OAuth callbacks
        """
        # For headless clients, we need a mechanism to handle OAuth callbacks
        # This could be through a local HTTP server or web interface
        return f"http://localhost:8080/oauth/callback/{self.server_id}"

    def client_metadata(self) -> OAuthClientMetadata:
        """Get OAuth client metadata for Smithery servers.

        Returns:
            Dict containing client metadata for the OAuth provider
        """
        return {
            "client_name": self.client_name,
            "client_uri": "https://github.com/SK-DEV-AI/ollmcp-marketplace",
            "redirect_uris": [self.redirect_url()],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "mangos:0",  # Standard Smithery scope for MCP access
            "token_endpoint_auth_method": "none"
        }

    def client_information(self) -> Optional[OAuthClientInformation]:
        """Get client information when required by the server.

        Returns:
            Optional client information dict
        """
        return {
            "client_id": "mcp-client-for-ollama",
            "client_name": self.client_name,
            "client_uri": "https://github.com/SK-DEV-AI/ollmcp-marketplace",
            "redirect_uris": [self.redirect_url()],
            "metadata": self.client_metadata()
        }

    def tokens(self) -> Optional[OAuthTokens]:
        """Get the current OAuth tokens for this server.

        Returns:
            OAuth tokens if available, None otherwise
        """
        return self._tokens

    async def save_tokens(self, tokens: OAuthTokens) -> None:
        """Save OAuth tokens to persistent storage.

        Args:
            tokens: The OAuth tokens to save
        """
        self._tokens = tokens

        # Create config directory if it doesn't exist
        os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)

        # Save tokens to file using server ID
        token_file = self._get_token_file_path()
        token_data = {
            "server_url": self.server_url,
            "tokens": {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "token_type": tokens.get("token_type", "Bearer"),
                "expires_in": tokens.get("expires_in"),
                "expires_at": tokens.get("expires_at"),
                "scope": tokens.get("scope")
            }
        }

        with open(token_file, 'w') as f:
            json.dump(token_data, f, indent=2)

    async def redirect_to_authorization(self, url: str) -> None:
        """Redirect to the OAuth authorization endpoint.

        This method should handle the OAuth flow. For headless clients,
        this might involve opening a browser or setting up a local callback server.

        Args:
            url: The authorization URL to redirect to
        """
        print(f"🔗 Opening OAuth authorization URL: {url}")
        print(f"⚠️ For headless clients, please:")
        print(f"1. Copy and open this URL in your browser")
        print(f"2. Complete the OAuth authorization")
        print(f"3. Copy the authorization code from the redirect URL")
        print(f"4. Enter the code when prompted")
        print(f"\nOr integrate with a web interface for seamless OAuth flow.")

        # For now, we'll need manual intervention
        # Future: Add browser automation or local HTTP server for callbacks

    async def save_code_verifier(self, verifier: str) -> None:
        """Save the OAuth PKCE code verifier.

        Args:
            verifier: The code verifier to save
        """
        # Store code verifier (could be session storage or temporary file)
        self._code_verifier = verifier

    async def code_verifier(self) -> str:
        """Get the stored OAuth PKCE code verifier.

        Returns:
            The code verifier
        """
        if not hasattr(self, '_code_verifier'):
            raise ValueError("No code verifier stored")
        return self._code_verifier

    def _extract_server_id(self, server_url: str) -> str:
        """Extract a unique server identifier from the URL.

        Args:
            server_url: The server URL

        Returns:
            A unique server identifier
        """
        # Extract server name from URL
        # E.g., "https://server.smithery.ai/@mark3labs/mcp-filesystem-server/mcp"
        # becomes: "@mark3labs/mcp-filesystem-server"
        if "smithery.ai" in server_url:
            parts = server_url.split("/")
            # Find the @ symbol and take everything from there until /mcp
            for i, part in enumerate(parts):
                if part.startswith("@"):
                    # Join parts from @ to the MCP path
                    server_id = "/".join(parts[i:i+2])  # Take @owner/repo
                    return server_id.replace("/", "_")  # Sanitize for filename

        # Fallback to URL hash
        return str(hash(server_url) % 1000000).replace('-', '')

    def _get_token_file_path(self) -> str:
        """Get the file path where OAuth tokens should be stored.

        Returns:
            Path to the token file
        """
        return os.path.join(DEFAULT_CONFIG_DIR, f"oauth_tokens_{self.server_id}.json")

    def _load_stored_tokens(self) -> Optional[OAuthTokens]:
        """Load stored OAuth tokens from file.

        Returns:
            OAuth tokens if available and valid, None otherwise
        """
        token_file = self._get_token_file_path()
        if not os.path.exists(token_file):
            return None

        try:
            with open(token_file, 'r') as f:
                data = json.load(f)

            tokens = data.get("tokens", {})
            if not tokens.get("access_token"):
                return None

            # Check if token is expired
            # This is a simple implementation - you might want more sophisticated expiry checking
            expires_at = tokens.get("expires_at")
            if expires_at:
                import time
                if time.time() > expires_at:
                    print(f"⚠️ OAuth token for {self.server_url} has expired")
                    return None

            return tokens

        except Exception as e:
            print(f"Error loading OAuth tokens for {self.server_url}: {e}")
            return None

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
        else:
            return None
