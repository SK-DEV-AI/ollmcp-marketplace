import asyncio
import httpx
import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession

from .smithery_client import SmitheryClient
from .hub_config_manager import MCPHubConfigManager
from ..config.manager import ConfigManager

class MCPHubManager:
    """Manages the MCP-HUB TUI."""

    def __init__(self, console: Console, smithery_client: SmitheryClient, main_config_manager: ConfigManager, client, config_name: str):
        self.console = console
        self.smithery_client = smithery_client
        self.main_config_manager = main_config_manager
        self.client = client
        self.config_name = config_name
        self.prompt_session = PromptSession()
        self.hub_config_manager = MCPHubConfigManager()
        self.api_key = self.main_config_manager.load_configuration(self.config_name).get("smithery_api_key")

    async def run(self):
        self.console.print(Panel(Text("Welcome to the MCP-HUB!", justify="center"), border_style="green"))
        if not self.api_key:
            self.console.print("[yellow]Smithery API key is not set. Some actions will require it.[/yellow]")
        while True:
            self.print_menu()
            try:
                choice = await self.prompt_session.prompt_async("Enter your choice: ", is_password=False)
                if choice == "1": await self.search_and_add_server()
                elif choice == "2": await self.uninstall_server()
                elif choice == "3": await self.view_installed_servers()
                elif choice == "4": await self.toggle_server_enabled_status()
                elif choice == "5": await self.reconfigure_server()
                elif choice == "6": await self.inspect_server_from_registry()
                elif choice == "7": await self.configure_api_key()
                elif choice == "8": self.clear_api_cache()
                elif choice in ["9", "q", "quit"]: break
                else: self.console.print("[red]Invalid choice.[/red]")
            except (KeyboardInterrupt, EOFError): break

    def print_menu(self):
        menu_text = """
[bold]MCP-HUB Menu[/bold]
1. Search and Add Servers
2. Uninstall a server
3. View installed servers
4. Enable/Disable a server
5. Re-configure installed server
6. Inspect server from registry
7. Configure Smithery API Key
8. Clear API Cache
9. Back to main menu (q, quit)
"""
        self.console.print(Panel(Text.from_markup(menu_text), title="MCP-HUB", border_style="yellow"))

    async def _ensure_api_key(self):
        if not self.api_key:
            self.console.print("[bold yellow]A Smithery API key is required.[/bold yellow]")
            await self.configure_api_key()
        return self.api_key is not None

    async def search_and_add_server(self):
        if not await self._ensure_api_key(): return
        try:
            while True:
                query = await self.prompt_session.prompt_async("Search query: ", is_password=False)
                with self.console.status("Searching..."):
                    results = await self.smithery_client.search_servers(query, self.api_key)
                if not results or "servers" not in results: self.console.print("[red]Invalid response from server.[/red]"); continue

                servers = results.get("servers", [])
                if not servers: self.console.print("[yellow]No servers found.[/yellow]"); continue

                tasks = [self.smithery_client.get_server(s["qualifiedName"], self.api_key) for s in servers]
                detailed_servers = await asyncio.gather(*tasks)

                for i, server in enumerate(detailed_servers): self._display_server_card(server, i + 1)

                action = await self.prompt_session.prompt_async("Enter ID to Add, (s)earch again, or (q)uit: ", is_password=False)
                if action.lower() == 'q': break
                if action.lower() == 's': continue
                try:
                    server_index = int(action) - 1
                    if 0 <= server_index < len(detailed_servers):
                        await self.add_server(detailed_servers[server_index])
                    else: self.console.print("[red]Invalid ID.[/red]")
                except (ValueError, IndexError): self.console.print("[red]Invalid input.[/red]")
        except Exception as e: self.console.print(f"[red]An unexpected error occurred: {e}[/red]")

    def _display_server_card(self, server, index):
        if not server: return
        display_name = server.get("displayName", server.get("qualifiedName"))
        q_name = server.get("qualifiedName")
        panel_title = f"({index}) [bold cyan]{display_name}[/bold cyan]  [dim]({q_name})[/dim]"
        description = server.get("description", "N/A")
        homepage = server.get("homepage", "N/A")
        link = f"[link={homepage}]{homepage}[/link]" if homepage != "N/A" else "N/A"
        security_info = server.get("security") or {}
        scan_passed = "[bold green]Yes[/bold green]" if security_info.get("scanPassed") else "[bold red]No[/bold red]"
        card_content = f"[bold]Description:[/bold] {description}\n[bold]Homepage:[/bold] {link} | [bold]Security Scan Passed:[/bold] {scan_passed}"
        self.console.print(Panel(Text.from_markup(card_content), title=Text.from_markup(panel_title), border_style="blue"))

    async def add_server(self, server_details):
        server_name = server_details.get("qualifiedName")
        if not server_name or server_name in self.hub_config_manager.get_servers():
            self.console.print(f"[yellow]Server '{server_name}' is already added.[/yellow]"); return

        conn_info = (server_details.get("connections") or [{}])[0]
        conn_type = conn_info.get("type")
        server_config = {}

        if conn_type in ["http", "shttp", "sse"]:
            server_config["type"] = "streamable_http" if conn_type != "sse" else "sse"
            server_config["url"] = conn_info.get("url")
            if not server_config["url"]: self.console.print(f"[red]Server '{server_name}' is missing a URL.[/red]"); return
        elif conn_type == "stdio":
            self.console.print(Panel(f"This is a `stdio` server and must be run locally.\nPlease clone it from: [blue underline]{server_details.get('homepage')}[/blue underline]", title="Manual Setup Required"))
            local_path = await self.prompt_session.prompt_async("Enter the absolute local path to the main script: ", is_password=False)
            if not os.path.exists(local_path): self.console.print(f"[red]Path not found: {local_path}[/red]"); return
            server_config["command"] = "python" if local_path.endswith(".py") else "node"
            server_config["args"] = [local_path]
        else:
            self.console.print(f"[red]Unsupported server type '{conn_type}'.[/red]"); return

        user_config = await self._ask_for_server_config(server_details)
        if user_config is None: return
        server_config.update(user_config)

        self.hub_config_manager.add_server(server_name, server_config)
        self.console.print(f"[green]Server '{server_name}' added to mcp.json.[/green]")
        await self.client.reload_servers()

    async def _select_installed_server(self, prompt_text):
        servers = self.hub_config_manager.get_servers()
        if not servers: self.console.print("[yellow]No servers are added.[/yellow]"); return None, None

        server_list = list(servers.items())
        for i, (name, config) in enumerate(server_list):
            status = "[dim](disabled)[/dim]" if config.get("disabled") else ""
            self.console.print(f"  ({i+1}) [cyan]{name}[/cyan] {status}")

        choice = await self.prompt_session.prompt_async(f"Enter ID to {prompt_text}: ", is_password=False)
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(server_list): return server_list[idx]
        except (ValueError, IndexError): pass
        self.console.print("[red]Invalid selection.[/red]"); return None, None

    async def uninstall_server(self):
        name, _ = await self._select_installed_server("uninstall")
        if name:
            self.hub_config_manager.remove_server(name)
            self.console.print(f"[green]Server '{name}' removed.[/green]")
            await self.client.reload_servers()

    async def view_installed_servers(self):
        servers = self.hub_config_manager.get_servers()
        if not servers: self.console.print("[yellow]No servers are added.[/yellow]"); return
        self.console.print(Panel(json.dumps({"mcpServers": servers}, indent=2), title="mcp.json content"))

    async def toggle_server_enabled_status(self):
        name, config = await self._select_installed_server("enable/disable")
        if not name: return

        current_disabled = config.get("disabled", False)
        config["disabled"] = not current_disabled
        self.hub_config_manager.add_server(name, config)
        status = "Enabled" if current_disabled else "Disabled"
        self.console.print(f"Server '{name}' is now {status}.")
        await self.client.reload_servers()

    async def reconfigure_server(self):
        name, old_config = await self._select_installed_server("re-configure")
        if not name or not await self._ensure_api_key(): return

        with self.console.status("Fetching latest details..."):
            details = await self.smithery_client.get_server(name, self.api_key)
        if not details: self.console.print("[red]Could not fetch details.[/red]"); return

        user_config = await self._ask_for_server_config(details)
        if user_config is None: return

        old_config.update(user_config)
        self.hub_config_manager.add_server(name, old_config)
        self.console.print(f"[green]Server '{name}' re-configured.[/green]")
        await self.client.reload_servers()

    async def inspect_server_from_registry(self):
        if not await self._ensure_api_key(): return
        name = await self.prompt_session.prompt_async("Enter server name to inspect: ", is_password=False)
        if not name: return
        with self.console.status("Fetching details..."):
            details = await self.smithery_client.get_server(name, self.api_key)
        if details: self._display_server_card(details, ">")

    async def configure_api_key(self):
        api_key = await self.prompt_session.prompt_async("Enter Smithery API Key: ", is_password=True)
        if api_key:
            config_data = self.main_config_manager.load_configuration(self.config_name)
            config_data["smithery_api_key"] = api_key
            self.main_config_manager.save_configuration(config_data, self.config_name)
            self.api_key = api_key
            self.console.print("[green]API Key saved.[/green]")

    def clear_api_cache(self):
        self.smithery_client.clear_cache()
        self.console.print(Panel("[bold green]API server cache cleared.[/bold green]"))

    async def _ask_for_server_config(self, server_details: dict):
        config = {}
        try:
            conn_info = (server_details.get("connections") or [{}])[0]
            schema = conn_info.get("configSchema")
            if not (schema and "properties" in schema): return {}

            self.console.print(Panel("Please configure the server:", title="Configuration"))
            for key, prop in schema["properties"].items():
                desc = prop.get("description", key)
                default = prop.get("default")
                prompt = f"{desc}" + (f" (default: {default})" if default is not None else "")
                val = await self.prompt_session.prompt_async(f"{prompt}: ", is_password=False)
                config[key] = val if val else default
            return config
        except (KeyboardInterrupt, EOFError):
            return None
