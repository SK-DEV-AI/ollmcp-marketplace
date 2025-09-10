import httpx
from ..config.manager import ConfigManager
import logging


class SmitheryClient:
    """A client for the Smithery Registry API."""

    def __init__(self, config_manager: ConfigManager, config_name: str = "default"):
        """Initialize the SmitheryClient.

        Args:
            config_manager: ConfigManager instance for loading API key.
            config_name: Name of the configuration to use for API key.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"SmitheryClient initialized with config_name={config_name}")
        self.config_manager = config_manager
        self.config_name = config_name
        self.api_key = None  # Will be loaded on demand
        self.base_url = "https://registry.smithery.ai"
        self.server_cache = {}

    def get_api_key(self) -> str | None:
        """Retrieves the Smithery API key from the current configuration."""
        config_data = self.config_manager.load_configuration(self.config_name)
        self.api_key = config_data.get("smithery_api_key")
        return self.api_key

    def set_api_key(self, api_key: str):
        """Saves the Smithery API key to the current configuration."""
        config_data = self.config_manager.load_configuration(self.config_name)
        config_data["smithery_api_key"] = api_key
        self.config_manager.save_configuration(config_data, self.config_name)
        self.api_key = api_key

    async def search_servers(self, query: str = "", page: int = 1, page_size: int = 10) -> dict:
        """Searches for servers on the Smithery Registry.

        Args:
            query: Search query string.
            page: Page number for pagination.
            page_size: Number of results per page.

        Returns:
            dict: Search results or empty dict on error.
        """
        if not self.api_key:
            self.logger.warning("Smithery API key is not set.")
            raise ValueError("Smithery API key is not set.")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"q": query, "page": page, "pageSize": page_size}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/servers", headers=headers, params=params
                )
                response.raise_for_status()
                data = response.json()
                return data or {}
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error during search: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            self.logger.error(f"Network error during search: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected error during search: {e}")
            return {}

    async def get_server(self, server_id: str) -> dict:
        """Gets the details of a single server, using a cache.

        Args:
            server_id: The ID of the server to retrieve.

        Returns:
            dict: Server details or empty dict on error.
        """
        if server_id in self.server_cache:
            return self.server_cache[server_id]

        if not self.api_key:
            self.logger.warning("Smithery API key is not set.")
            raise ValueError("Smithery API key is not set.")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/servers/{server_id}", headers=headers
                )
                response.raise_for_status()
                data = response.json()
                # Cache the data only if it's not None, but always return a dict
                if data:
                    self.server_cache[server_id] = data
                return data or {}
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error during get_server: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            self.logger.error(f"Network error during get_server: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected error during get_server: {e}")
            return {}

    def clear_cache(self):
        """Clears the in-memory server cache."""
        self.server_cache = {}
