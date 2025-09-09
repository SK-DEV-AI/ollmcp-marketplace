import asyncio
import functools
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession
from rich.table import Table

from .smithery_client import SmitheryClient
from ..config.manager import ConfigManager


class MCPHubManager:
    """Manages the MCP-HUB TUI."""

    def __init__(self, console: Console, smithery_client: SmitheryClient, config_manager: ConfigManager, client, config_name: str):
        self.console = console
        self.smithery_client = smithery_client
        self.config_manager = config_manager
        self.client = client
        self.config_name = config_name
        self.prompt_session = PromptSession()

    async def run(self):
        """Runs the main loop of the MCP-HUB."""
        self.console.print(Panel(Text("Welcome to the MCP-HUB!", justify="center"), border_style="green"))
        while True:
            self.print_menu()
            try:
                choice = await self.prompt_session.prompt_async("Enter your choice: ", is_password=False)
                if choice == "1":
                    await self.search_servers()
                elif choice == "2":
                    await self.uninstall_server()
                elif choice == "3":
                    await self.view_installed_servers()
                elif choice == "4":
                    await self.toggle_server_enabled_status()
                elif choice == "5":
                    await self.reconfigure_server()
                elif choice == "6":
                    await self.inspect_server_from_registry()
                elif choice == "7":
                    await self.configure_api_key()
                elif choice == "8":
                    self.clear_api_cache()
                elif choice in ["9", "q", "quit"]:
                    break
                else:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")
            except (KeyboardInterrupt, EOFError):
                break

    def print_menu(self):
        """Prints the MCP-HUB menu."""
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

    async def search_servers(self):
        """Handles the server search workflow and subsequent actions."""
        try:
            while True:
                self.console.print(Panel("You can use filters like 'owner:username' or 'is:verified'.", title="Advanced Search Tip", style="dim", border_style="blue"))
                query = await self.prompt_session.prompt_async("Enter search query: ", is_password=False)
                with self.console.status("Searching..."):
                    results = await self.smithery_client.search_servers(query)

                if not results:
                    self.console.print("[red]Received an empty or invalid response from the server.[/red]")
                    continue

                servers = results.get("servers", [])
                if not servers:
                    self.console.print("[yellow]No servers found.[/yellow]")
                    continue

                self.console.print(Panel(f"Found {len(servers)} server(s).", border_style="green"))

                tasks = [self.smithery_client.get_server(s["qualifiedName"]) for s in servers]
                detailed_servers = await asyncio.gather(*tasks, return_exceptions=True)

                for i, server in enumerate(detailed_servers):
                    if isinstance(server, Exception) or not server:
                        continue

                    display_name = server.get("displayName", server.get("qualifiedName"))
                    description = server.get("description", "No description available.")
                    tool_count = str(len(server.get("tools", [])))
                    homepage = server.get("homepage", "N/A")
                    link = f"[link={homepage}]{homepage}[/link]" if homepage != "N/A" else homepage
                    q_name = server.get("qualifiedName")

                    security_info = server.get("security") or {}
                    scan_passed = security_info.get("scanPassed", False)
                    scan_text = "[bold green]Yes[/bold green]" if scan_passed else "[bold red]No[/bold red]"

                    card_content = f"[bold]Description:[/bold] {description}\n"
                    card_content += f"[bold]Tools:[/bold] {tool_count} | [bold]Homepage:[/bold] {link} | [bold]Security Scan Passed:[/bold] {scan_text}"

                    panel_title = f"({i + 1}) [bold cyan]{display_name}[/bold cyan]  [dim]({q_name})[/dim]"

                    self.console.print(Panel(
                        Text.from_markup(card_content),
                        title=Text.from_markup(panel_title),
                        border_style="blue",
                        expand=True
                    ))

                # New unified workflow prompt
                action = await self.prompt_session.prompt_async(
                    "Enter an ID to install, (s)earch again, or (q)uit to menu: ",
                    is_password=False
                )

                if action.lower() == 'q':
                    break
                elif action.lower() == 's':
                    continue
                else:
                    try:
                        server_index = int(action) - 1
                        if 0 <= server_index < len(detailed_servers):
                            selected_server = detailed_servers[server_index]
                            # Call add_server, passing the details to avoid a second API call
                            await self.add_server(server_details=selected_server)
                        else:
                            self.console.print("[red]Invalid ID.[/red]")
                    except (ValueError, IndexError):
                        self.console.print("[red]Invalid input. Please enter a valid ID, 's', or 'q'.[/red]")

        except ValueError as e:
            if "API key is not set" in str(e):
                self.console.print("[bold yellow]A Smithery API key is required to search for servers.[/bold yellow]")
                await self.configure_api_key()
                if self.smithery_client.api_key:
                    self.console.print("[green]API Key set. Please try your search again.[/green]")
                else:
                    self.console.print("[yellow]Search cancelled because API key was not provided.[/yellow]")
            else:
                self.console.print(f"[red]An unexpected value error occurred: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]An unexpected error occurred during search: {e}[/red]")

    async def add_server(self, server_details: dict = None):
        """Handles the server installation workflow."""
        server_name = ""
        try:
            # If server details aren't passed, we're in the old workflow: prompt for name and fetch
            if server_details is None:
                server_name = await self.prompt_session.prompt_async("Enter the name of the server to install: ", is_password=False)
                if not server_name:
                    return

                with self.console.status(f"Getting details for {server_name}..."):
                    server_details = await self.smithery_client.get_server(server_name)

            # Use the qualifiedName from the provided details
            server_name = server_details.get("qualifiedName")

            installed_servers = self.config_manager.get_installed_servers(self.config_name)
            if any(s.get("qualifiedName") == server_name for s in installed_servers):
                self.console.print(f"[yellow]Server '{server_name}' is already installed.[/yellow]")
                return

            security_info = server_details.get("security") or {}
            scan_passed = security_info.get("scanPassed", False)
            scan_text = "[bold green]Yes[/bold green]" if scan_passed else "[bold red]No[/bold red]"

            self.console.print(Panel(f"[bold]Name:[/bold] {server_details.get('displayName')}\n"
                                   f"[bold]Description:[/bold] {server_details.get('description')}\n"
                                   f"[bold]Security Scan Passed:[/bold] {scan_text}"))

            # Check connection type and handle stdio servers differently
            connection_info = (server_details.get("connections") or [{}])[0]
            conn_type = connection_info.get("type")

            if conn_type == "stdio":
                self.console.print(Panel(
                    "[bold yellow]This is a `stdio` server that must be run locally.[/bold yellow]\n\n"
                    "1. Please clone the server's repository to your local machine.\n"
                    f"   Git URL: [blue underline]{server_details.get('homepage')}[/blue underline]\n\n"
                    "2. Enter the absolute path to the server's main executable script below.",
                    title="Manual Setup Required"
                ))
                local_path = await self.prompt_session.prompt_async("Enter local script path: ", is_password=False)

                import os
                if not os.path.exists(local_path):
                    self.console.print(f"[red]Error: Path not found: {local_path}[/red]")
                    return

                # Store the local path for the connector to use
                server_details["local_script_path"] = local_path

            config = await self._ask_for_server_config(server_details)
            if config is None:
                return

            server_details["config"] = config
            server_details["enabled"] = True

            self.config_manager.add_installed_server(server_details, self.config_name)

            summary_text = f"[bold]Name:[/bold] {server_details.get('displayName')}\n"
            summary_text += f"[bold]Description:[/bold] {server_details.get('description')}\n\n"
            summary_text += "[bold]Configuration:[/bold]\n"
            if config:
                for key, value in config.items():
                    summary_text += f"  - {key}: {value}\n"
            else:
                summary_text += "  - No configuration required."

            self.console.print(Panel(Text.from_markup(summary_text), title="[bold green]Installation Successful[/bold green]", border_style="green"))

            await self.client.reload_servers()

        except ValueError as e:
            if "API key is not set" in str(e):
                self.console.print("[bold yellow]A Smithery API key is required to install servers.[/bold yellow]")
                await self.configure_api_key()
                if self.smithery_client.api_key:
                    self.console.print("[green]API Key set. Please try installing the server again.[/green]")
                else:
                    self.console.print("[yellow]Installation cancelled because API key was not provided.[/yellow]")
            else:
                self.console.print(f"[red]An unexpected value error occurred: {e}[/red]")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.console.print(f"[red]Server '{server_name}' not found in the registry.[/red]")
            else:
                self.console.print(f"[red]Error fetching server details: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]An unexpected error occurred during installation: {e}[/red]")

    async def uninstall_server(self):
        """Handles the server uninstallation workflow."""
        try:
            installed_servers = self.config_manager.get_installed_servers(self.config_name)
            if not installed_servers:
                self.console.print("[yellow]No servers installed.[/yellow]")
                return

            table = Table(title="Installed Servers")
            table.add_column("ID", style="magenta")
            table.add_column("Display Name", style="cyan")
            table.add_column("Qualified Name", style="dim")

            for i, server in enumerate(installed_servers):
                table.add_row(str(i + 1), server.get('displayName'), server.get('qualifiedName'))

            self.console.print(table)

            choice = await self.prompt_session.prompt_async("Enter the ID of the server to uninstall (or press Enter to cancel): ", is_password=False)
            if not choice:
                return

            server_index = int(choice) - 1
            if not (0 <= server_index < len(installed_servers)):
                self.console.print("[red]Invalid ID.[/red]")
                return

            server_to_uninstall = installed_servers[server_index]
            server_name = server_to_uninstall.get("qualifiedName")

            self.config_manager.remove_installed_server(server_name, self.config_name)
            self.console.print(f"[green]Server '{server_name}' has been uninstalled.[/green]")

            with self.console.status("Reloading servers to apply changes..."):
                await self.client.reload_servers()
            self.console.print("[green]Server has been removed from the current session.[/green]")

        except Exception as e:
            self.console.print(f"[red]Error uninstalling server: {e}[/red]")

    async def view_installed_servers(self):
        """Displays details for installed servers."""
        self.console.print(Panel("Viewing installed servers...", border_style="blue"))
        installed_servers = self.config_manager.get_installed_servers(self.config_name)

        if not installed_servers:
            self.console.print("[yellow]No servers are currently installed.[/yellow]")
            return

        table = Table(title="Installed MCP Servers")
        table.add_column("ID", style="magenta")
        table.add_column("Display Name", style="cyan")
        table.add_column("Qualified Name", style="dim")

        for i, server in enumerate(installed_servers):
            table.add_row(str(i + 1), server.get('displayName'), server.get('qualifiedName'))

        self.console.print(table)

        try:
            choice = await self.prompt_session.prompt_async("Enter the ID of the server to view (or press Enter to return): ", is_password=False)
            if not choice:
                return

            server_index = int(choice) - 1
            if 0 <= server_index < len(installed_servers):
                server = installed_servers[server_index]

                summary_text = f"[bold]Display Name:[/bold] {server.get('displayName')}\n"
                summary_text += f"[bold]Qualified Name:[/bold] {server.get('qualifiedName')}\n"
                summary_text += f"[bold]Description:[/bold] {server.get('description')}\n"
                summary_text += f"[bold]Homepage:[/bold] [link={server.get('homepage')}]{server.get('homepage')}[/link]\n\n"
                summary_text += "[bold]Saved Configuration:[/bold]\n"

                config = server.get("config", {})
                if config:
                    for key, value in config.items():
                        summary_text += f"  - {key}: {value}\n"
                else:
                    summary_text += "  - No configuration was required or set for this server."

                self.console.print(Panel(Text.from_markup(summary_text), title="[bold cyan]Server Details[/bold cyan]", border_style="cyan", expand=False))
            else:
                self.console.print("[red]Invalid ID.[/red]")
        except (ValueError, IndexError):
            self.console.print("[red]Invalid input. Please enter a valid number.[/red]")
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n")

    async def inspect_server_from_registry(self):
        """Fetches and displays details for any server from the registry."""
        server_name = ""
        try:
            server_name = await self.prompt_session.prompt_async("Enter the qualified name of the server to inspect: ", is_password=False)
            if not server_name:
                return

            with self.console.status(f"Fetching details for {server_name}..."):
                server = await self.smithery_client.get_server(server_name)

            security_info = server.get("security") or {}
            scan_passed = security_info.get("scanPassed", False)
            scan_text = "[bold green]Yes[/bold green]" if scan_passed else "[bold red]No[/bold red]"

            summary_text = f"[bold]Display Name:[/bold] {server.get('displayName')}\n"
            summary_text += f"[bold]Qualified Name:[/bold] {server.get('qualifiedName')}\n"
            summary_text += f"[bold]Description:[/bold] {server.get('description')}\n"
            summary_text += f"[bold]Homepage:[/bold] [link={server.get('homepage')}]{server.get('homepage')}[/link]\n"
            summary_text += f"[bold]Security Scan Passed:[/bold] {scan_text}\n\n"
            summary_text += "[bold]Tools:[/bold]\n"

            tools = server.get("tools", [])
            if tools:
                for tool in tools:
                    summary_text += f"  - {tool.get('name')}: {tool.get('description')}\n"
            else:
                summary_text += "  - No tools listed for this server."

            self.console.print(Panel(Text.from_markup(summary_text), title="[bold cyan]Registry Server Details[/bold cyan]", border_style="cyan", expand=False))

        except ValueError as e:
            if "API key is not set" in str(e):
                self.console.print("[bold yellow]A Smithery API key is required to inspect servers.[/bold yellow]")
                await self.configure_api_key()
                if self.smithery_client.api_key:
                    self.console.print("[green]API Key set. Please try inspecting the server again.[/green]")
                else:
                    self.console.print("[yellow]Action cancelled because API key was not provided.[/yellow]")
            else:
                self.console.print(f"[red]An unexpected value error occurred: {e}[/red]")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.console.print(f"[red]Server '{server_name}' not found in the registry.[/red]")
            else:
                self.console.print(f"[red]Error fetching server details: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]An unexpected error occurred: {e}[/red]")

    async def toggle_server_enabled_status(self):
        """Allows enabling or disabling an installed server."""
        try:
            installed_servers = self.config_manager.get_installed_servers(self.config_name)
            if not installed_servers:
                self.console.print("[yellow]No servers are currently installed.[/yellow]")
                return

            table = Table(title="Enable/Disable Servers")
            table.add_column("ID", style="magenta")
            table.add_column("Display Name", style="cyan")
            table.add_column("Status", style="dim")

            for i, server in enumerate(installed_servers):
                status = "[bold green]Enabled[/bold green]" if server.get("enabled", True) else "[bold red]Disabled[/bold red]"
                table.add_row(str(i + 1), server.get('displayName'), status)

            self.console.print(table)

            choice = await self.prompt_session.prompt_async("Enter the ID of the server to toggle (or press Enter to cancel): ", is_password=False)
            if not choice:
                return

            server_index = int(choice) - 1
            if not (0 <= server_index < len(installed_servers)):
                self.console.print("[red]Invalid ID.[/red]")
                return

            server_to_toggle = installed_servers[server_index]
            current_status = server_to_toggle.get("enabled", True)
            server_to_toggle["enabled"] = not current_status

            config_data = self.config_manager.load_configuration(self.config_name)
            config_data["installed_servers"] = installed_servers
            self.config_manager.save_configuration(config_data, self.config_name)

            new_status = "[bold green]Enabled[/bold green]" if not current_status else "[bold red]Disabled[/bold red]"
            self.console.print(f"Server '{server_to_toggle.get('displayName')}' is now {new_status}.")

            with self.console.status("Reloading servers to apply changes..."):
                await self.client.reload_servers()

        except (ValueError, IndexError):
            self.console.print("[red]Invalid input. Please enter a valid number.[/red]")
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n")

    async def reconfigure_server(self):
        """Allows re-configuring an already installed server."""
        try:
            installed_servers = self.config_manager.get_installed_servers(self.config_name)
            if not installed_servers:
                self.console.print("[yellow]No servers are currently installed.[/yellow]")
                return

            table = Table(title="Re-configure Server")
            table.add_column("ID", style="magenta")
            table.add_column("Display Name", style="cyan")

            for i, server in enumerate(installed_servers):
                table.add_row(str(i + 1), server.get('displayName'))

            self.console.print(table)

            choice = await self.prompt_session.prompt_async("Enter the ID of the server to re-configure (or press Enter to cancel): ", is_password=False)
            if not choice:
                return

            server_index = int(choice) - 1
            if not (0 <= server_index < len(installed_servers)):
                self.console.print("[red]Invalid ID.[/red]")
                return

            server_to_reconfigure = installed_servers[server_index]
            server_name = server_to_reconfigure.get("qualifiedName")

            with self.console.status(f"Fetching latest details for {server_name}..."):
                latest_details = await self.smithery_client.get_server(server_name)

            self.console.print(f"Re-configuring '{latest_details.get('displayName')}'. Please provide the new configuration:")
            new_config = await self._ask_for_server_config(latest_details)

            if new_config is None:
                self.console.print("[yellow]Re-configuration cancelled.[/yellow]")
                return

            installed_servers[server_index]["config"] = new_config
            config_data = self.config_manager.load_configuration(self.config_name)
            config_data["installed_servers"] = installed_servers
            self.config_manager.save_configuration(config_data, self.config_name)

            self.console.print(f"[green]Server '{server_name}' has been re-configured successfully.[/green]")

            with self.console.status("Reloading servers to apply changes..."):
                await self.client.reload_servers()

        except (ValueError, IndexError):
            self.console.print("[red]Invalid input. Please enter a valid number.[/red]")
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n")

    async def _ask_for_server_config(self, server_details: dict) -> dict | None:
        """Asks the user for server configuration based on a schema."""
        config = {}
        try:
            if "connections" in server_details and server_details["connections"]:
                config_schema = server_details["connections"][0].get("configSchema")
                if not (config_schema and "properties" in config_schema):
                    return {}

                self.console.print(Panel("Please configure the server:", title="Configuration", border_style="yellow"))
                for key, prop in config_schema["properties"].items():
                    prop_type = prop.get("type", "string")
                    prop_desc = prop.get("description", f"Enter value for {key}")
                    prop_default = prop.get("default")

                    prompt_text = f"{prop_desc}"
                    if prop_default is not None:
                        prompt_text += f" (default: {prop_default})"

                    if prop_type == "boolean":
                        while True:
                            raw_value = await self.prompt_session.prompt_async(f"{prompt_text} (y/n): ", is_password=False)
                            if not raw_value and prop_default is not None:
                                value = bool(prop_default)
                                break
                            if raw_value.lower() in ["y", "yes"]:
                                value = True
                                break
                            if raw_value.lower() in ["n", "no"]:
                                value = False
                                break
                            self.console.print("[red]Invalid input. Please enter 'y' or 'n'.[/red]")
                    elif prop_type in ["number", "integer"]:
                        while True:
                            raw_value = await self.prompt_session.prompt_async(f"{prompt_text}: ", is_password=False)
                            if not raw_value and prop_default is not None:
                                value = prop_default
                                break
                            try:
                                value = int(raw_value) if prop_type == "integer" else float(raw_value)
                                break
                            except ValueError:
                                self.console.print(f"[red]Invalid input. Please enter a valid {prop_type}.[/red]")
                    else:
                        raw_value = await self.prompt_session.prompt_async(f"{prompt_text}: ", is_password=False)
                        value = raw_value if raw_value else prop_default

                    config[key] = value
            return config
        except (KeyboardInterrupt, EOFError):
            return None

    def clear_api_cache(self):
        """Clears the Smithery API client's in-memory cache."""
        self.smithery_client.clear_cache()
        self.console.print(Panel("[bold green]API server cache has been cleared.[/bold green]"))

    async def configure_api_key(self):
        """Handles the API key configuration workflow."""
        self.console.print("[green]Configuring Smithery API Key...[/green]")
        try:
            api_key = await self.prompt_session.prompt_async("Enter your Smithery API Key: ", is_password=True)
            if api_key:
                self.smithery_client.set_api_key(api_key, self.config_name)
                self.console.print("[green]API Key saved successfully.[/green]")
            else:
                self.console.print("[yellow]API Key configuration cancelled.[/yellow]")
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]API Key configuration cancelled.[/yellow]")
