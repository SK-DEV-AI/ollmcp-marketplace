import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession

from .smithery_client import SmitheryClient
from ..config.manager import ConfigManager

class MCPHubManager:
    """Manages the MCP-HUB TUI."""

    def __init__(self, console: Console, smithery_client: SmitheryClient, config_manager: ConfigManager, client):
        self.console = console
        self.smithery_client = smithery_client
        self.config_manager = config_manager
        self.client = client
        self.prompt_session = PromptSession()

    async def run(self):
        """Runs the main loop of the MCP-HUB."""
        self.console.print(Panel(Text("Welcome to the MCP-HUB!", justify="center"), border_style="blue"))
        while True:
            self.print_menu()
            try:
                choice = await self.prompt_session.prompt_async("Enter your choice: ")
                if choice == "1":
                    await self.search_servers()
                elif choice == "2":
                    await self.install_server()
                elif choice == "3":
                    await self.uninstall_server()
                elif choice == "4":
                    await self.configure_api_key()
                elif choice in ["5", "q", "quit"]:
                    break
                else:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")
            except (KeyboardInterrupt, EOFError):
                break

    def print_menu(self):
        """Prints the MCP-HUB menu."""
        menu_text = """
[bold]MCP-HUB Menu[/bold]
1. Search for servers
2. Install a server
3. Uninstall a server
4. Configure Smithery API Key
5. Back to main menu (q, quit)
"""
        self.console.print(Panel(Text.from_markup(menu_text), title="MCP-HUB", border_style="blue"))

    async def search_servers(self):
        """Handles the server search workflow."""
        try:
            query = await self.prompt_session.prompt_async("Enter search query (or leave blank to list all): ")
            with self.console.status("Searching..."):
                results = await self.smithery_client.search_servers(query)

            servers = results.get("servers", [])
            if not servers:
                self.console.print("[yellow]No servers found.[/yellow]")
                return

            from rich.table import Table
            table = Table(title="Search Results")
            table.add_column("Name", style="cyan")
            table.add_column("Description")
            table.add_column("Use Count", style="magenta")
            table.add_column("Tools", style="green")

            # Fetch details in parallel
            tasks = [self.smithery_client.get_server(s["qualifiedName"]) for s in servers]
            detailed_servers = await asyncio.gather(*tasks, return_exceptions=True)

            for server in detailed_servers:
                if isinstance(server, Exception):
                    # Handle cases where a server detail fetch might fail
                    continue
                tool_count = len(server.get("tools", []))
                table.add_row(
                    server.get('qualifiedName'),
                    server.get('description'),
                    str(server.get('useCount')),
                    str(tool_count)
                )

            self.console.print(table)

        except Exception as e:
            self.console.print(f"[red]Error searching for servers: {e}[/red]")

    async def install_server(self):
        """Handles the server installation workflow."""
        try:
            server_name = await self.prompt_session.prompt_async("Enter the name of the server to install: ")
            with self.console.status(f"Getting details for {server_name}..."):
                server_details = await self.smithery_client.get_server(server_name)

            self.console.print(Panel(f"[bold]Name:[/bold] {server_details.get('displayName')}\n"
                                   f"[bold]Description:[/bold] {server_details.get('description')}"))

            # Handle configuration
            config = {}
            if "connections" in server_details and server_details["connections"]:
                config_schema = server_details["connections"][0].get("configSchema")
                if config_schema and "properties" in config_schema:
                    for key, prop in config_schema["properties"].items():
                        prompt = prop.get("description", f"Enter value for {key}")
                        value = await self.prompt_session.prompt_async(f"{prompt}: ")
                        config[key] = value

            server_details["config"] = config

            # Save the server to the configuration
            self.config_manager.add_installed_server(server_details)
            self.console.print(f"[green]Server '{server_name}' installed successfully.[/green]")

            # Reload servers
            await self.client.reload_servers()

        except Exception as e:
            self.console.print(f"[red]Error installing server: {e}[/red]")

    async def uninstall_server(self):
        """Handles the server uninstallation workflow."""
        try:
            installed_servers = self.config_manager.get_installed_servers()
            if not installed_servers:
                self.console.print("[yellow]No servers installed.[/yellow]")
                return

            from rich.table import Table
            table = Table(title="Installed Servers")
            table.add_column("Name", style="cyan")
            table.add_column("Description")

            for server in installed_servers:
                table.add_row(server.get('qualifiedName'), server.get('description'))

            self.console.print(table)

            server_name = await self.prompt_session.prompt_async("Enter the name of the server to uninstall: ")

            self.config_manager.remove_installed_server(server_name)
            self.console.print(f"[green]Server '{server_name}' uninstalled successfully.[/green]")

        except Exception as e:
            self.console.print(f"[red]Error uninstalling server: {e}[/red]")

    async def configure_api_key(self):
        """Handles the API key configuration workflow."""
        self.console.print("[green]Configuring Smithery API Key...[/green]")
        try:
            api_key = await self.prompt_session.prompt_async("Enter your Smithery API Key: ", is_password=True)
            self.smithery_client.set_api_key(api_key)
            self.console.print("[green]API Key saved successfully.[/green]")
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]API Key configuration cancelled.[/yellow]")
