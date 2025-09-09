import httpx

class SmitheryClient:
    """A stateless client for the Smithery Registry API."""

    def __init__(self):
        self.base_url = "https://registry.smithery.ai"
        self.server_cache = {}

    def clear_cache(self):
        """Clears the in-memory server cache."""
        self.server_cache = {}

    async def search_servers(self, query: str, api_key: str, page: int = 1, page_size: int = 10) -> dict:
        """Searches for servers on the Smithery Registry."""
        if not api_key:
            raise ValueError("API key is required for search.")

        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"q": query, "page": page, "pageSize": page_size}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/servers", headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data or {}

    async def get_server(self, server_id: str, api_key: str) -> dict:
        """Gets the details of a single server, using a cache."""
        if server_id in self.server_cache:
            return self.server_cache[server_id]

        if not api_key:
            raise ValueError("API key is required to get server details.")

        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/servers/{server_id}", headers=headers)
            response.raise_for_status()
            data = response.json()
            if data:
                self.server_cache[server_id] = data
            return data or {}
