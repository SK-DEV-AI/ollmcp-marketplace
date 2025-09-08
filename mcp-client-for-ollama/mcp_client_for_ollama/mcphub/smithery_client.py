import httpx
from ..config.manager import ConfigManager

class SmitheryClient:
    """A client for the Smithery Registry API."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.api_key = self.get_api_key()
        self.base_url = "https://registry.smithery.ai"

    def get_api_key(self) -> str | None:
        """Retrieves the Smithery API key from the configuration."""
        return self.config_manager.get_config().get("smithery_api_key")

    def set_api_key(self, api_key: str):
        """Saves the Smithery API key to the configuration."""
        config_data = self.config_manager.get_config()
        config_data["smithery_api_key"] = api_key
        self.config_manager.save_configuration(config_data)
        self.api_key = api_key

    async def search_servers(self, query: str = "", page: int = 1, page_size: int = 10):
        """Searches for servers on the Smithery Registry."""
        if not self.api_key:
            raise ValueError("Smithery API key is not set.")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"q": query, "page": page, "pageSize": page_size}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/servers", headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    async def get_server(self, server_id: str):
        """Gets the details of a single server."""
        if not self.api_key:
            raise ValueError("Smithery API key is not set.")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/servers/{server_id}", headers=headers)
            response.raise_for_status()
            return response.json()
