import httpx
from ..config.manager import ConfigManager

class SmitheryClient:
    """A client for the Smithery Registry API."""

    def __init__(self, config_manager: ConfigManager, config_name: str):
        self.config_manager = config_manager
        self.config_name = config_name
        self.api_key = self.get_api_key()
        self.base_url = "https://registry.smithery.ai"
        self.server_cache = {}

    def get_api_key(self) -> str | None:
        """Retrieves the Smithery API key from the configuration."""
        # A specific config name might not exist yet, so we load it to check
        config_data = self.config_manager.load_configuration(self.config_name)
        return config_data.get("smithery_api_key")

    def set_api_key(self, api_key: str):
        """Saves the Smithery API key to the configuration."""
        config_data = self.config_manager.load_configuration(self.config_name)
        config_data["smithery_api_key"] = api_key
        self.config_manager.save_configuration(config_data, self.config_name)
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
        """Gets the details of a single server, using a cache."""
        if server_id in self.server_cache:
            return self.server_cache[server_id]

        if not self.api_key:
            raise ValueError("Smithery API key is not set.")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/servers/{server_id}", headers=headers)
            response.raise_for_status()
            data = response.json()
            self.server_cache[server_id] = data
            return data

    def clear_cache(self):
        """Clears the in-memory server cache."""
        self.server_cache = {}
