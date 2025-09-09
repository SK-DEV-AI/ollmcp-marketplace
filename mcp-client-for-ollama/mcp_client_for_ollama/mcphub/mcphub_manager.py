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
                elif choice == "9":
                    await self.check_server_health()
                elif choice == "10":
                    await self.backup_restore_configuration()
                elif choice == "11":
                    await self.view_server_categories()
                elif choice in ["12", "q", "quit"]:
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
9. Check server health status
10. Backup/Restore configuration
11. View server categories
12. Back to main menu (q, quit)
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

            # Extract connection information from the Smithery API response and ensure it's saved properly
            if "connections" in server_details and server_details["connections"]:
                connection_info = server_details["connections"][0]
                conn_type = connection_info.get("type")
                conn_url = connection_info.get("url")

                # For HTTP/SSE servers, save the URL explicitly to ensure persistence
                if conn_type in ["shttp", "http", "sse"] and conn_url:
                    # Ensure we have a connections array in the right format for the connector
                    server_details["connections"] = [connection_info]
                elif conn_type == "stdio" and server_details.get("local_script_path"):
                    # For stdio servers, ensure local path is saved properly
                    server_details["local_script_path"] = server_details["local_script_path"]

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

            choice = await self.prompt_session.prompt_async("Enter the ID(s) of the server(s) to uninstall (supports ranges like 1-3, spaces like 1 3 5, or press Enter to cancel): ", is_password=False)
            if not choice:
                return

            # Parse the input to handle ranges and space-separated inputs
            server_indices = self._parse_server_indices(choice, len(installed_servers))
            if not server_indices:
                self.console.print("[red]No valid server IDs found in input.[/red]")
                return

            # Remove servers in reverse order to avoid index shifting issues
            removed_servers = []
            for server_index in sorted(server_indices, reverse=True):
                if 0 <= server_index < len(installed_servers):
                    server_to_uninstall = installed_servers[server_index]
                    server_name = server_to_uninstall.get("qualifiedName")
                    removed_servers.append(server_name)
                    # Remove from installed_servers list
                    installed_servers.pop(server_index)

            if not removed_servers:
                self.console.print("[red]No servers were uninstalled.[/red]")
                return

            # Update the configuration with the remaining servers
            config_data = self.config_manager.load_configuration(self.config_name)
            config_data["installed_servers"] = installed_servers
            self.config_manager.save_configuration(config_data, self.config_name)

            if len(removed_servers) == 1:
                self.console.print(f"[green]Server '{removed_servers[0]}' has been uninstalled.[/green]")
            else:
                removed_list = ", ".join([f"'{name}'" for name in removed_servers])
                self.console.print(f"[green]The following {len(removed_servers)} servers have been uninstalled: {removed_list}[/green]")

            with self.console.status("Reloading servers to apply changes..."):
                await self.client.reload_servers()
            self.console.print("[green]Servers have been removed from the current session.[/green]")

        except Exception as e:
            self.console.print(f"[red]Error uninstalling server: {e}[/red]")

    def _parse_server_indices(self, input_str: str, max_index: int) -> list:
        """Parse server indices from input string supporting ranges and space-separated values.

        Args:
            input_str: Input string like "1-3", "1 3 5", or "2"
            max_index: Maximum valid index (length of installed servers)

        Returns:
            List of valid server indices (0-based)
        """
        indices = set()

        # Split by spaces first
        parts = input_str.strip().split()

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check if it's a range (contains '-')
            if '-' in part:
                try:
                    range_parts = part.split('-')
                    if len(range_parts) == 2:
                        start = int(range_parts[0].strip()) - 1  # Convert to 0-based
                        end = int(range_parts[1].strip()) - 1    # Convert to 0-based

                        if 0 <= start <= end < max_index:
                            for i in range(start, end + 1):
                                indices.add(i)
                        else:
                            self.console.print(f"[yellow]Warning: Invalid range '{part}', ignoring[/yellow]")
                except ValueError:
                    self.console.print(f"[yellow]Warning: Invalid range format '{part}', ignoring[/yellow]")
            else:
                # It's a single number
                try:
                    server_index = int(part) - 1  # Convert to 0-based
                    if 0 <= server_index < max_index:
                        indices.add(server_index)
                    else:
                        self.console.print(f"[yellow]Warning: Server ID '{part}' is out of range, ignoring[/yellow]")
                except ValueError:
                    self.console.print(f"[yellow]Warning: Invalid server ID '{part}', ignoring[/yellow]")

        return sorted(list(indices))

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

            choice = await self.prompt_session.prompt_async("Enter the ID(s) of the server(s) to toggle (supports ranges like 1-3, spaces like 1 3 5, or press Enter to cancel): ", is_password=False)
            if not choice:
                return

            # Parse the input to handle ranges and space-separated inputs
            server_indices = self._parse_server_indices(choice, len(installed_servers))
            if not server_indices:
                self.console.print("[red]No valid server IDs found in input.[/red]")
                return

            # Toggle each selected server
            toggled_servers = []
            for server_index in server_indices:
                server_to_toggle = installed_servers[server_index]
                current_status = server_to_toggle.get("enabled", True)
                server_to_toggle["enabled"] = not current_status
                new_status = "[bold green]Enabled[/bold green]" if not current_status else "[bold red]Disabled[/bold red]"
                toggled_servers.append(f"{server_to_toggle.get('displayName')} ({new_status})")

            # Update the configuration
            config_data = self.config_manager.load_configuration(self.config_name)
            config_data["installed_servers"] = installed_servers
            self.config_manager.save_configuration(config_data, self.config_name)

            if len(toggled_servers) == 1:
                self.console.print(f"[green]Server status toggled: {toggled_servers[0]}[/green]")
            else:
                self.console.print("[green]Server status toggled:[/green]")
                for toggled in toggled_servers:
                    self.console.print(f"  - {toggled}")

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

    async def check_server_health(self):
        """Check the health status of installed servers."""
        try:
            installed_servers = self.config_manager.get_installed_servers(self.config_name)
            if not installed_servers:
                self.console.print("[yellow]No servers are currently installed.[/yellow]")
                return

            self.console.print(Panel("[bold]Checking Server Health Status[/bold]", border_style="blue"))

            health_table = Table(title="Server Health Status")
            health_table.add_column("Server", style="cyan", width=25)
            health_table.add_column("Status", style="green", width=10)
            health_table.add_column("Connection", style="dim", width=15)
            health_table.add_column("Details", style="yellow")

            from ..utils.connection import check_url_connectivity
            import os

            for server in installed_servers:
                server_name = server.get("displayName", server.get("qualifiedName"))
                connection_info = server.get("connections", [{}])

                if not connection_info:
                    health_table.add_row(server_name, "[red]Error[/red]", "None", "No connection info")
                    continue

                conn_info = connection_info[0]
                conn_type = conn_info.get("type")
                conn_url = conn_info.get("url")

                if conn_type in ["http", "shttp", "sse"]:
                    if conn_url:
                        is_connected = check_url_connectivity(conn_url)
                        status = "[green]Healthy[/green]" if is_connected else "[red]Connection Failed[/red]"
                        conn_status = "Online" if is_connected else "Failed"
                    else:
                        status = "[red]Error[/red]"
                        conn_status = "Missing URL"
                elif conn_type == "stdio":
                    local_path = server.get("local_script_path") or conn_info.get("path")
                    if local_path and os.path.exists(local_path):
                        status = "[green]Ready[/green]"
                        conn_status = "Local File"
                    else:
                        status = "[red]Error[/red]"
                        conn_status = "File Missing"
                else:
                    status = "[yellow]Unknown[/yellow]"
                    conn_status = f"Type: {conn_type}"

                enabled_status = "[green]Enabled[/green]" if server.get("enabled", True) else "[dim]Disabled[/dim]"
                details = enabled_status

                health_table.add_row(server_name, status, conn_status, details)

            self.console.print(health_table)

            # Summary
            healthy_servers = sum(1 for s in installed_servers
                                if s.get("enabled", True) and
                                (s.get("connections", [{}])[0].get("url") or s.get("local_script_path")))

            disabled_servers = sum(1 for s in installed_servers
                                 if not s.get("enabled", True))

            self.console.print(Panel(
                f"[bold]Health Summary:[/bold]\n"
                f"• {healthy_servers} servers healthy\n"
                f"• {disabled_servers} servers disabled\n"
                f"• {len(installed_servers)} total servers",
                title="Summary", border_style="green"
            ))

        except Exception as e:
            self.console.print(f"[red]Error checking server health: {e}[/red]")

    async def backup_restore_configuration(self):
        """Backup or restore server configuration."""
        try:
            self.console.print(Panel(
                "[bold]Configuration Backup/Restore[/bold]\n\n"
                "1. Backup current configuration\n"
                "2. Restore from backup\n"
                "3. Export servers list\n"
                "4. Import servers from file",
                title="Configuration Options",
                border_style="blue"
            ))

            choice = await self.prompt_session.prompt_async("Choose an option (1-4) or press Enter to cancel: ", is_password=False)
            if not choice or choice not in ["1", "2", "3", "4"]:
                return

            if choice == "1":
                await self._backup_configuration()
            elif choice == "2":
                await self._restore_configuration()
            elif choice == "3":
                await self._export_servers_list()
            elif choice == "4":
                await self._import_servers_list()

        except Exception as e:
            self.console.print(f"[red]Error in backup/restore: {e}[/red]")

    async def _backup_configuration(self):
        """Create a backup of the current configuration."""
        try:
            import json
            import datetime
            import os

            config_data = self.config_manager.load_configuration(self.config_name)
            if not config_data.get("installed_servers"):
                self.console.print("[yellow]No servers installed to backup.[/yellow]")
                return

            # Create backup filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(os.path.expanduser("~"), ".ollmcp_backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = os.path.join(backup_dir, f"ollmcp_backup_{self.config_name}_{timestamp}.json")

            with open(backup_file, 'w') as f:
                json.dump(config_data, f, indent=2)

            self.console.print(Panel(
                f"[green]✅ Configuration backed up successfully![/green]\n\n"
                f"[bold]File:[/bold] {backup_file}\n"
                f"[bold]Servers backed up:[/bold] {len(config_data.get('installed_servers', []))}\n\n"
                f"[dim]Backup created at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
                title="Backup Successful", border_style="green"
            ))

        except Exception as e:
            self.console.print(f"[red]Error creating backup: {e}[/red]")

    async def _restore_configuration(self):
        """Restore configuration from a backup file."""
        try:
            import os
            import json

            backup_dir = os.path.join(os.path.expanduser("~"), ".ollmcp_backups")

            if not os.path.exists(backup_dir):
                self.console.print("[yellow]No backup directory found. Create a backup first.[/yellow]")
                return

            backup_files = [f for f in os.listdir(backup_dir)
                          if f.startswith(f"ollmcp_backup_{self.config_name}") and f.endswith(".json")]

            if not backup_files:
                self.console.print(f"[yellow]No backups found for configuration '{self.config_name}'.[/yellow]")
                return

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)

            self.console.print("\n[bold]Available Backups:[/bold]")
            for i, backup_file in enumerate(backup_files[:5]):  # Show latest 5
                mod_time = os.path.getmtime(os.path.join(backup_dir, backup_file))
                formatted_time = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                self.console.print(f"{i+1}. {backup_file} (modified: {formatted_time})")

            if len(backup_files) > 5:
                self.console.print(f"[dim]... and {len(backup_files) - 5} more[/dim]")

            choice = await self.prompt_session.prompt_async(
                f"Enter backup number to restore (1-{min(5, len(backup_files))}) or press Enter to cancel: ",
                is_password=False
            )

            if not choice:
                return

            try:
                backup_index = int(choice) - 1
                if not (0 <= backup_index < len(backup_files)):
                    raise ValueError("Invalid index")

                selected_backup = backup_files[backup_index]
                backup_path = os.path.join(backup_dir, selected_backup)

                # Confirm restoration
                confirm = await self.prompt_session.prompt_async(
                    f"[bold red]⚠️  This will overwrite your current configuration![/bold red]\n"
                    f"Are you sure you want to restore from '{selected_backup}'? (y/N): ",
                    is_password=False
                )

                if confirm.lower() not in ["y", "yes"]:
                    self.console.print("[yellow]Restoration cancelled.[/yellow]")
                    return

                # Load and restore backup
                with open(backup_path, 'r') as f:
                    backup_config = json.load(f)

                self.config_manager.save_configuration(backup_config, self.config_name)

                servers_restored = len(backup_config.get("installed_servers", []))
                self.console.print(Panel(
                    f"[green]✅ Configuration restored successfully![/green]\n\n"
                    f"[bold]Restored from:[/bold] {selected_backup}\n"
                    f"[bold]Servers restored:[/bold] {servers_restored}\n\n"
                    f"[dim]Configuration reloaded. Some servers may need to be reloaded.[/dim]",
                    title="Restore Successful", border_style="green"
                ))

                # Reload servers to apply changes
                with self.console.status("Reloading servers..."):
                    await self.client.reload_servers()

            except (ValueError, IndexError):
                self.console.print("[red]Invalid backup number.[/red]")
            except Exception as e:
                self.console.print(f"[red]Error during restoration: {e}[/red]")

        except Exception as e:
            self.console.print(f"[red]Error in restore operation: {e}[/red]")

    async def _export_servers_list(self):
        """Export list of installed servers to a text file."""
        try:
            import json
            import datetime
            import os

            config_data = self.config_manager.load_configuration(self.config_name)
            installed_servers = config_data.get("installed_servers", [])

            if not installed_servers:
                self.console.print("[yellow]No servers installed to export.[/yellow]")
                return

            export_data = {
                "export_timestamp": datetime.datetime.now().isoformat(),
                "config_name": self.config_name,
                "servers": []
            }

            for server in installed_servers:
                export_server = {
                    "qualified_name": server.get("qualifiedName"),
                    "display_name": server.get("displayName"),
                    "description": server.get("description", ""),
                    "homepage": server.get("homepage"),
                    "enabled": server.get("enabled", True),
                    "connection_type": (server.get("connections", [{}])[0] or {}).get("type", "unknown")
                }
                export_data["servers"].append(export_server)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = f"ollmcp_servers_export_{self.config_name}_{timestamp}.json"

            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2)

            self.console.print(Panel(
                f"[green]✅ Server list exported successfully![/green]\n\n"
                f"[bold]File:[/bold] {export_file}\n"
                f"[bold]Servers exported:[/bold] {len(installed_servers)}\n\n"
                f"[dim]Export created at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
                title="Export Successful", border_style="green"
            ))

        except Exception as e:
            self.console.print(f"[red]Error exporting servers: {e}[/red]")

    async def _import_servers_list(self):
        """Import servers from an exported file."""
        try:
            import json

            export_file = await self.prompt_session.prompt_async("Enter the path to the exported servers file: ", is_password=False)
            if not export_file:
                return

            if not os.path.exists(export_file):
                self.console.print(f"[red]File not found: {export_file}[/red]")
                return

            with open(export_file, 'r') as f:
                import_data = json.load(f)

            if "servers" not in import_data:
                self.console.print("[red]Invalid export file format.[/red]")
                return

            servers = import_data["servers"]
            self.console.print(f"Found {len(servers)} servers in the export file.")

            # Option to import all or select specific ones
            import_all = await self.prompt_session.prompt_async("Import all servers? (y/N): ", is_password=False)

            servers_to_import = []
            if import_all.lower() in ["y", "yes"]:
                servers_to_import = servers
            else:
                # Show server list and let user select
                self.console.print("\n[bold]Available servers to import:[/bold]")
                for i, server in enumerate(servers):
                    status = "[green]✓[/green]" if server.get("enabled", True) else "[red]✗[/red]"
                    self.console.print(f"{i+1}. {status} {server.get('display_name')}")

                selection = await self.prompt_session.prompt_async(
                    f"Enter server numbers to import (supports ranges like 1-3, spaces like 1 3 5): ",
                    is_password=False
                )

                if not selection:
                    return

                selected_indices = self._parse_server_indices(selection, len(servers))
                servers_to_import = [servers[i] for i in selected_indices]

            if not servers_to_import:
                self.console.print("[yellow]No servers selected for import.[/yellow]")
                return

            # Fetch full server details and install them
            imported_count = 0
            for server in servers_to_import:
                try:
                    qualified_name = server.get("qualified_name")
                    if not qualified_name:
                        continue

                    with self.console.status(f"Fetching details for {qualified_name}..."):
                        server_details = await self.smithery_client.get_server(qualified_name)

                    # Preserve enabled status from import
                    server_details["enabled"] = server.get("enabled", True)

                    # Install the server
                    await self.add_server(server_details=server_details)
                    imported_count += 1

                except Exception as e:
                    self.console.print(f"[red]Failed to import server '{server.get('display_name')}': {e}[/red]")

            self.console.print(Panel(
                f"[green]✅ Import completed![/green]\n\n"
                f"[bold]Servers imported:[/bold] {imported_count}/{len(servers_to_import)}",
                title="Import Results", border_style="green"
            ))

        except Exception as e:
            self.console.print(f"[red]Error importing servers: {e}[/red]")

    async def view_server_categories(self):
        """View servers organized by categories within the registry."""
        try:
            self.console.print(Panel("Choose a category or view popular/trending servers:", title="Server Categories", border_style="blue"))

            categories = [
                ("trending", "🔥 Trending Servers"),
                ("verified", "✓ Verified Servers"),
                ("recent", "🆕 Recently Added"),
                ("popular", "⭐ Popular Servers"),
                ("filesystem", "📁 File System Tools"),
                ("web", "🌐 Web/HTTP Servers"),
                ("database", "🗄️ Database Tools"),
                ("ai", "🧠 AI/ML Tools"),
                ("search", "🔍 Search & Research"),
                ("development", "💻 Development Tools")
            ]

            for i, (key, display) in enumerate(categories):
                self.console.print(f"{i+1}. {display}")

            choice = await self.prompt_session.prompt_async(f"Choose a category (1-{len(categories)}) or press Enter to cancel: ", is_password=False)
            if not choice:
                return

            try:
                category_index = int(choice) - 1
                if not (0 <= category_index < len(categories)):
                    raise ValueError("Invalid choice")

                selected_category, display_name = categories[category_index]

                # Build query based on category
                query_parts = []
                if selected_category == "verified":
                    query_parts.append("is:verified")
                elif selected_category == "trending":
                    query_parts.append("sort:trending")
                elif selected_category == "recent":
                    query_parts.append("sort:recent")
                elif selected_category == "popular":
                    query_parts.append("sort:popular")
                elif selected_category == "filesystem":
                    query_parts.append("filesystem OR file OR storage")
                elif selected_category == "web":
                    query_parts.append("http OR web OR api")
                elif selected_category == "database":
                    query_parts.append("database OR sql OR mongo")
                elif selected_category == "ai":
                    query_parts.append("ai OR ml OR machine learning")
                elif selected_category == "search":
                    query_parts.append("search OR research OR query")
                elif selected_category == "development":
                    query_parts.append("dev OR build OR tool")

                query = " ".join(query_parts)

                with self.console.status(f"Searching for {display_name.lower()}..."):
                    results = await self.smithery_client.search_servers(query)

                if not results:
                    self.console.print(f"[yellow]No {display_name.lower().replace('🔥 ', '')} found with the current search.[/yellow]")
                    return

                servers = results.get("servers", [])
                if not servers:
                    self.console.print("[yellow]No servers found in this category.[/yellow]")
                    return

                self.console.print(Panel(f"Found {len(servers)} {display_name.lower()}", border_style="green"))

                # Display servers in this category
                tasks = [self.smithery_client.get_server(s["qualifiedName"]) for s in servers[:10]]  # Limit to first 10
                detailed_servers = await asyncio.gather(*tasks, return_exceptions=True)

                for i, server in enumerate(detailed_servers):
                    if isinstance(server, Exception) or not server:
                        continue

                    display_name_server = server.get("displayName", server.get("qualifiedName"))
                    description = server.get("description", "No description available.")
                    tool_count = str(len(server.get("tools", [])))

                    card_content = f"[bold]Description:[/bold] {description}\n"
                    card_content += f"[bold]Tools:[/bold] {tool_count}"

                    panel_title = f"({i + 1}) [bold cyan]{display_name_server}[/bold cyan]"

                    self.console.print(Panel(
                        Text.from_markup(card_content),
                        title=Text.from_markup(panel_title),
                        border_style="blue",
                        expand=True
                    ))

                # Prompt for installation
                action = await self.prompt_session.prompt_async(
                    "Enter an ID to install or press Enter to return: ",
                    is_password=False
                )

                if action:
                    try:
                        server_index = int(action) - 1
                        if 0 <= server_index < len(detailed_servers):
                            selected_server = detailed_servers[server_index]
                            if not isinstance(selected_server, Exception):
                                await self.add_server(server_details=selected_server)
                    except (ValueError, IndexError):
                        self.console.print("[red]Invalid ID.[/red]")

            except (ValueError, IndexError):
                self.console.print("[red]Invalid choice.[/red]")

        except Exception as e:
            self.console.print(f"[red]Error viewing categories: {e}[/red]")
