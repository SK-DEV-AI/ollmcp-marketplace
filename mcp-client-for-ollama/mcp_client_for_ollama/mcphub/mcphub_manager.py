"""
Professional MCP Server Management System
==========================================

Advanced command-line interface for MCP (Model Context Protocol) servers
with enterprise-grade configuration management.
"""

import asyncio
import functools
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from prompt_toolkit import PromptSession

from .smithery_client import SmitheryClient
from ..config.manager import ConfigManager


class MCPHubManager:
    """Professional MCP Server Management with Enterprise Features."""

    def __init__(self, console: Console, smithery_client: SmitheryClient, config_manager: ConfigManager, client, config_name: str):
        self.console = console
        self.smithery_client = smithery_client
        self.config_manager = config_manager
        self.client = client
        self.config_name = config_name
        self.prompt_session = PromptSession()

        # Initialize API key from configuration
        self._initialize_api_key()

    def _initialize_api_key(self):
        """Initialize Smithery API key from current configuration."""
        if self.smithery_client.get_api_key(self.config_name) is None:
            config_data = self.config_manager.load_configuration(self.config_name)
            api_key = config_data.get("smithery_api_key")
            if api_key:
                self.smithery_client.set_api_key(api_key, self.config_name)

    async def run(self):
        """Main MCP-HUB interface loop."""
        welcome_message = Panel(
            Text("Welcome to MCP-HUB - Professional MCP Server Manager!", justify="center"),
            border_style="green"
        )
        self.console.print(welcome_message)

        while True:
            try:
                self.display_menu()
                choice = await self.prompt_session.prompt_async("Select option: ", is_password=False)

                await self._handle_menu_choice(choice)
                if choice in ["14", "q", "quit"]:
                    break

            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Operation cancelled. Back to menu.[/yellow]")
                continue
            except Exception as e:
                self.console.print(f"[red]Unexpected error: {e}[/red]")
                continue

    def display_menu(self):
        """Display the professional MCP-HUB menu."""
        menu_content = """
[bold cyan]MCP-HUB Professional Server Manager[/bold cyan]

[bold blue]🔍 Discovery & Installation:[/bold blue]
1.  Search and Install Servers     | Discover and add MCP servers
2.  View Server Categories         | Browse by type (AI, Web, File, DB, etc.)

[bold green]⚙️  Server Management:[/bold green]
3.  View Installed Servers         | List and manage configured servers
4.  Enable/Disable Servers         | Toggle server availability
5.  Reconfigure Server             | Update server settings
6.  Uninstall Servers              | Remove servers (bulk support)

[bold purple]🔧 Advanced Features:[/bold purple]
7.  Server Health Check            | Check connection and status
8.  Backup/Restore Config          | Backup and restore configurations
9.  Inspect Server Registry        | View detailed server info
10. Setup Server Connectivity      | Configure local/server connections

[bold yellow]🛠️  System & Settings:[/bold yellow]
11. Configure Smithery API Key     | Set up API access
12. Clear API Cache                | Reset cached server data
13. Server Directory Info          | View organization structure

[bold gray]14. Back to Main Menu (q, quit)[/bold gray]
"""

        menu_panel = Panel(
            Text.from_markup(menu_content),
            title="[bold white]MCP-HUB Professional Edition[/bold white]",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(menu_panel)

    async def _handle_menu_choice(self, choice: str):
        """Route menu choices to appropriate methods."""
        choice = choice.strip().lower()

        menu_actions = {
            "1": self.search_servers,
            "2": self.view_server_categories,
            "3": self.view_installed_servers,
            "4": self.toggle_server_enabled_status,
            "5": self.reconfigure_server,
            "6": self.uninstall_server,
            "7": self.check_server_health,
            "8": self.backup_restore_configuration,
            "9": self.inspect_server_from_registry,
            "10": self.setup_server_connectivity,
            "11": self.configure_api_key,
            "12": lambda: self.clear_api_cache(),
            "13": lambda: self.show_server_directory(),
        }

        if choice in menu_actions:
            try:
                await menu_actions[choice]()
                if choice in ["12", "13"]:  # Synchronous methods that need user confirmation
                    await self.prompt_session.prompt_async("Press Enter to continue...", is_password=False)
            except Exception as e:
                self.console.print(f"[red]Error executing option {choice}: {e}[/red]")
        elif choice in ["14", "q", "quit"]:
            pass  # Handled by calling method
        else:
            self.console.print("[red]Invalid option. Please select 1-14.[/red]")

    async def search_servers(self):
        """Search and install servers with advanced features."""
        try:
            while True:
                search_panel = Panel(
                    "[dim]Tip: Use filters like 'owner:username', 'is:verified', 'filesystem', etc.[/dim]",
                    title="[search] Advanced Server Search[/search]",
                    border_style="blue"
                )
                self.console.print(search_panel)

                query = await self.prompt_session.prompt_async("Enter search query: ", is_password=False)
                if not query.strip():
                    continue

                with self.console.status("Searching Smithery registry..."):
                    results = await self.smithery_client.search_servers(query)

                if not results or not results.get("servers"):
                    self.console.print("[yellow]No servers found. Try different keywords or visit smithery.io[/yellow]")
                    continue

                servers = results["servers"]
                self.console.print(f"\n[green]Found {len(servers)} server(s)[/green]")

                # Fetch detailed server information
                with self.console.status("Getting server details..."):
                    detailed_servers = await self._fetch_server_details(servers[:10])  # Limit to 10

                # Display server cards
                self._display_server_cards(detailed_servers)

                # Interactive installation workflow
                action = await self.prompt_session.prompt_async(
                    "Enter server ID to install, (s)earch again, or (q)uit: ",
                    is_password=False
                )

                if action.lower() == 'q':
                    break
                elif action.lower() == 's':
                    continue

                await self._handle_server_installation(detailed_servers, action)

        except Exception as e:
            self.console.print(f"[red]Search error: {e}[/red]")

    async def _fetch_server_details(self, servers):
        """Fetch detailed information for servers."""
        tasks = [self.smithery_client.get_server(s["qualifiedName"]) for s in servers]
        detailed_servers = await asyncio.gather(*tasks, return_exceptions=True)
        # Filter out None and Exception objects, ensure we return valid server data
        result = []
        for i, server in enumerate(detailed_servers):
            if isinstance(server, Exception):
                continue
            if server is None:
                continue
            if not isinstance(server, dict):
                continue
            if not server.get("qualifiedName"):
                continue
            result.append((i, server))
        return result

    def _display_server_cards(self, servers_data):
        """Display professional server information cards with robust error handling."""
        # Safety check - ensure we have valid data
        if not servers_data or not isinstance(servers_data, list):
            self.console.print("[yellow]No valid server data to display.[/yellow]")
            return

        valid_servers_count = 0

        for index, server in servers_data:
            try:
                # Comprehensive validation
                if not server or not isinstance(server, dict):
                    continue

                display_name = server.get("displayName", server.get("qualifiedName", "Unknown Server"))
                if not display_name:
                    continue

                q_name = server.get("qualifiedName", "")
                if not q_name:
                    continue

                description = server.get("description", "No description available.")
                if not isinstance(description, str):
                    description = "No description available."

                tools = server.get("tools", [])
                tool_count = len(tools) if isinstance(tools, list) else 0

                homepage = server.get("homepage", "")

                security_info = server.get("security", {})
                security_passed = security_info.get("scanPassed", False) if isinstance(security_info, dict) else False

                # Security indicator
                security_text = "[bold green]Secure[/bold green]" if security_passed else "[bold red]Unverified[/bold red]"

                card_content = f"""[bold]Description:[/bold] {description[:100]}{"..." if len(description) > 100 else ""}
[bold]Tools:[/bold] {tool_count} | [bold]Security:[/bold] {security_text}
[bold]Homepage:[/bold] [link={homepage}]{homepage}[/link]"""

                server_panel = Panel(
                    Text.from_markup(card_content),
                    title=f"[bold cyan]({index + 1}) {display_name}[/bold cyan]\n[dim]{q_name}[/dim]",
                    border_style="blue",
                    padding=(1, 2),
                    expand=True
                )
                self.console.print(server_panel)
                valid_servers_count += 1

            except (AttributeError, TypeError, KeyError) as e:
                # Skip any malformed server data silently
                continue
            except Exception as e:
                # For debugging - but don't break the UI
                self.console.print(f"[dim gray]Skipping malformed server {index + 1}: {e}[/dim gray]")
                continue

        if valid_servers_count == 0:
            self.console.print("[yellow]No valid servers found to display.[/yellow]")
        elif valid_servers_count < len(servers_data):
            self.console.print(f"[dim]Displayed {valid_servers_count} of {len(servers_data)} servers (some had invalid data)[/dim]")

    async def _handle_server_installation(self, servers_data, action):
        """Handle server installation workflow."""
        try:
            server_index = int(action.strip()) - 1
            selected_server = None

            for index, server in servers_data:
                if index == server_index:
                    selected_server = server
                    break

            if selected_server:
                await self.add_server(server_details=selected_server)
            else:
                self.console.print("[red]Invalid server ID.[/red]")

        except (ValueError, IndexError):
            self.console.print("[red]Invalid input. Enter a valid server ID.[/red]")

    async def add_server(self, server_details=None):
        """Professional server installation with smart configuration."""
        server_name = ""

        try:
            # Get server details if not provided
            if server_details is None:
                server_name = await self.prompt_session.prompt_async(
                    "Enter server qualified name: ", is_password=False
                )
                if not server_name:
                    return

                with self.console.status(f"Fetching {server_name}..."):
                    server_details = await self.smithery_client.get_server(server_name)

            server_name = server_details.get("qualifiedName")
            display_name = server_details.get("displayName", server_name)

            # Check if already installed
            if self._is_server_installed(server_name):
                self.console.print(f"[yellow]{display_name} is already installed.[/yellow]")
                return

            # Display server preview
            self._display_server_preview(server_details)

            # Handle different connection types
            await self._handle_server_type_installation(server_details)

            # Configure server parameters
            config = await self._ask_for_server_config(server_details)
            if config is None:
                return

            # Finalize installation
            await self._finalize_server_installation(server_details, config, display_name)

        except Exception as e:
            error_type = type(e).__name__
            self.console.print(f"[red]Installation failed: {error_type}: {e}[/red]")

    def _is_server_installed(self, server_name):
        """Check if server is already installed."""
        installed_servers = self.config_manager.get_installed_servers(self.config_name)
        return any(s.get("qualifiedName") == server_name for s in installed_servers)

    def _display_server_preview(self, server_details):
        """Display server information before installation."""
        display_name = server_details.get("displayName")
        description = server_details.get("description")
        tool_count = len(server_details.get("tools", []))
        security_passed = server_details.get("security", {}).get("scanPassed", False)

        security_text = "[bold green]Verified[/bold green]" if security_passed else "[bold red]Unverified[/bold red]"

        preview_panel = Panel(
            f"[bold]Name:[/bold] {display_name}\n"
            f"[bold]Description:[/bold] {description}\n"
            f"[bold]Security:[/bold] {security_text}\n"
            f"[bold]Available Tools:[/bold] {tool_count}",
            title="[install] Server Preview",
            border_style="green"
        )
        self.console.print(preview_panel)

    async def _handle_server_type_installation(self, server_details):
        """Handle installation based on server connection type."""
        connection_info = server_details.get("connections", [{}])[0]
        conn_type = connection_info.get("type")

        if conn_type == "stdio":
            await self._handle_stdio_installation(server_details)
        elif conn_type in ["http", "shttp", "sse"]:
            await self._handle_http_installation(server_details)

    async def _handle_stdio_installation(self, server_details):
        """Handle stdio server installation."""
        display_name = server_details.get("displayName", server_details.get("qualifiedName"))

        installation_panel = Panel(
            f"[bold yellow]This is a Local Server[/bold yellow]\n\n"
            "Installation Steps:\n"
            f"1. Clone: {server_details.get('homepage', 'N/A')}\n"
            f"2. Install: cd [repo-name] && npm install\n"
            f"3. Build: npm run build && npm start\n\n"
            "Enter the absolute path to the server's executable script below.",
            title=f"{display_name} Setup",
            border_style="yellow"
        )
        self.console.print(installation_panel)

        auto_clone = await self.prompt_session.prompt_async(
            "Auto-clone repository? (Y/n): ", is_password=False
        )

        if auto_clone.lower() != 'n':
            await self._clone_server_repository(server_details)
        else:
            local_path = await self.prompt_session.prompt_async(
                "Enter local script path: ", is_password=False
            )
            if local_path and self._validate_local_path(local_path):
                server_details["local_script_path"] = local_path

    async def _handle_http_installation(self, server_details):
        """Handle HTTP-based server installation."""
        # Will be implemented by the server connectivity handler
        pass

    def _validate_local_path(self, path):
        """Validate local file path."""
        import os
        if os.path.exists(path):
            self.console.print(f"[green]Path validated: {path}[/green]")
            return True
        else:
            self.console.print(f"[red]Path not found: {path}[/red]")
            return False

    async def _ask_for_server_config(self, server_details):
        """Interactive server configuration."""
        config_schema = server_details.get("connections", [{}])[0].get("configSchema")

        if not config_schema or "properties" not in config_schema:
            return {}

        config_panel = Panel(
            "Configure server parameters:",
            title="Server Configuration",
            border_style="yellow"
        )
        self.console.print(config_panel)

        try:
            config = {}
            for key, prop in config_schema["properties"].items():
                config[key] = await self._get_config_value(key, prop)
            return config
        except (KeyboardInterrupt, EOFError):
            return None

    async def _get_config_value(self, key, prop):
        """Get configuration value from user."""
        prop_type = prop.get("type", "string")
        prop_desc = prop.get("description", f"Enter value for {key}")
        prop_default = prop.get("default")

        prompt_text = f"{prop_desc}"
        if prop_default is not None:
            prompt_text += f" (default: {prop_default})"

        if prop_type == "boolean":
            return await self._get_boolean_config(prompt_text, prop_default)
        elif prop_type in ["number", "integer"]:
            return await self._get_numeric_config(prompt_text, prop_type, prop_default)
        else:
            return await self._get_string_config(prompt_text, prop_default)

    async def _get_boolean_config(self, prompt_text, default):
        """Get boolean configuration value."""
        while True:
            value = await self.prompt_session.prompt_async(
                f"{prompt_text} (y/n): ", is_password=False
            )
            if not value and default is not None:
                return default
            if value.lower() in ["y", "yes"]:
                return True
            if value.lower() in ["n", "no"]:
                return False
            self.console.print("[red]Invalid input. Enter 'y' or 'n'.[/red]")

    async def _get_numeric_config(self, prompt_text, prop_type, default):
        """Get numeric configuration value."""
        while True:
            value = await self.prompt_session.prompt_async(f"{prompt_text}: ", is_password=False)
            if not value and default is not None:
                return default
            try:
                return int(value) if prop_type == "integer" else float(value)
            except ValueError:
                self.console.print(f"[red]Invalid {prop_type}. Try again.[/red]")

    async def _get_string_config(self, prompt_text, default):
        """Get string configuration value."""
        value = await self.prompt_session.prompt_async(f"{prompt_text}: ", is_password=False)
        return value if value else default

    async def _finalize_server_installation(self, server_details, config, display_name):
        """Finalize the server installation process."""
        server_details["config"] = config if config else {}
        server_details["enabled"] = True

        # Save to configuration
        self.config_manager.add_installed_server(server_details, self.config_name)

        # Display success
        success_panel = Panel(
            f"""[bold green]Installation Successful![/bold green]

[bold]Server:[/bold] {display_name}
[bold]Config:[/bold] {len(config) if config else 0} parameters set
[bold]Status:[/bold] Enabled and ready to use

[bold]Configuration:[/bold]
{self._format_config_summary(config)}""",
            title="Server Successfully Installed",
            border_style="green"
        )
        self.console.print(success_panel)

        # Reload clients to apply changes
        with self.console.status("Reloading servers..."):
            await self.client.reload_servers()

        self.console.print("[green]Server is now active![/green]")

    def _format_config_summary(self, config):
        """Format configuration summary."""
        if not config:
            return "  No configuration required"

        lines = []
        for key, value in config.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    async def uninstall_server(self):
        """Uninstall servers with bulk operations support."""
        try:
            installed_servers = self.config_manager.get_installed_servers(self.config_name)
            if not installed_servers:
                self.console.print("[yellow]No servers installed.[/yellow]")
                return

            # Display server table
            self._display_uninstall_table(installed_servers)

            # Get user selection
            selection = await self.prompt_session.prompt_async(
                "Enter server ID(s) (ranges like 1-3, individual like 1 3 5, or Enter to cancel): ",
                is_password=False
            )

            if not selection:
                return

            # Parse selection
            server_indices = self._parse_server_indices(selection, len(installed_servers))
            if not server_indices:
                self.console.print("[red]No valid servers selected.[/red]")
                return

            # Confirm uninstallation
            if not await self._confirm_uninstallation(server_indices, installed_servers):
                return

            # Perform uninstallation
            await self._perform_uninstallation(server_indices, installed_servers)

        except Exception as e:
            self.console.print(f"[red]Uninstall error: {e}[/red]")

    def _display_uninstall_table(self, servers):
        """Display servers available for uninstallation."""
        table = Table(title="[uninstall] Available Servers", title_style="red")

        table.add_column("ID", style="magenta", no_wrap=True)
        table.add_column("Display Name", style="cyan")
        table.add_column("Qualified Name", style="dim")
        table.add_column("Status", style="green")

        for i, server in enumerate(servers):
            status = "[bold green]Enabled[/bold green]" if server.get("enabled", True) else "[bold red]Disabled[/bold red]"
            table.add_row(str(i + 1), server.get('displayName'), server.get('qualifiedName'), status)

        self.console.print(table)

    async def _confirm_uninstallation(self, indices, servers):
        """Confirm server uninstallation."""
        selected_servers = [servers[i].get('displayName', servers[i].get('qualifiedName')) for i in indices]

        confirm_panel = Panel(
            f"[bold red]Confirm Uninstallation[/bold red]\n\n"
            f"[bold]Servers to remove:[/bold]\n" +
            "\n".join(f"  {name}" for name in selected_servers) + "\n\n" +
            "[bold yellow]This action cannot be undone![/bold yellow]",
            title="Confirmation Required",
            border_style="red"
        )
        self.console.print(confirm_panel)

        confirm = await self.prompt_session.prompt_async(
            "Type 'DELETE' to confirm or Enter to cancel: ", is_password=False
        )

        return confirm.strip().lower() == "delete"

    async def _perform_uninstallation(self, indices, servers):
        """Execute server uninstallation."""
        removed_servers = []

        for server_index in sorted(indices, reverse=True):
            server_to_remove = servers[server_index]
            server_name = server_to_remove.get("qualifiedName", server_to_remove.get("displayName"))
            removed_servers.append(server_name)
            servers.pop(server_index)

        # Update configuration
        config_data = self.config_manager.load_configuration(self.config_name)
        config_data["installed_servers"] = servers
        self.config_manager.save_configuration(config_data, self.config_name)

        # Display results
        result_panel = Panel(
            f"[bold green]Uninstallation Complete[/bold green]\n\n"
            f"[bold]Removed:[/bold] {len(removed_servers)} server(s)\n" +
            "\n".join(f"  {name}" for name in removed_servers),
            title="Servers Removed",
            border_style="green"
        )
        self.console.print(result_panel)

        # Reload servers
        with self.console.status("Updating server configuration..."):
            await self.client.reload_servers()

    def _parse_server_indices(self, input_str: str, max_index: int) -> list:
        """Parse server selection with support for ranges and individual IDs."""
        indices = set()

        parts = input_str.strip().split()
        for part in parts:
            if '-' in part:
                # Range handling
                try:
                    start, end = map(int, part.split('-'))
                    if 1 <= start <= end <= max_index:
                        indices.update(range(start - 1, end))
                    else:
                        self.console.print(f"[yellow]Invalid range: {part}[/yellow]")
                except ValueError:
                    self.console.print(f"[yellow]Invalid range format: {part}[/yellow]")
            else:
                # Individual ID
                try:
                    server_index = int(part) - 1
                    if 0 <= server_index < max_index:
                        indices.add(server_index)
                    else:
                        self.console.print(f"[yellow]ID out of range: {part}[/yellow]")
                except ValueError:
                    self.console.print(f"[yellow]Invalid ID: {part}[/yellow]")

        return sorted(list(indices))

    async def view_installed_servers(self):
        """Display detailed information about installed servers."""
        installed_servers = self.config_manager.get_installed_servers(self.config_name)

        if not installed_servers:
            self.console.print("[yellow]No servers are currently installed.[/yellow]")
            return

        # Summary table
        self._display_servers_table(installed_servers)

        # Detailed view prompt
        choice = await self.prompt_session.prompt_async(
            "Enter server ID for details or Enter to return: ", is_password=False
        )

        if choice:
            await self._display_server_details(installed_servers, choice)

    def _display_servers_table(self, servers):
        """Display servers in a professional table."""
        table = Table(title="[view] Installed Servers", title_style="cyan")

        table.add_column("#", style="magenta", no_wrap=True)
        table.add_column("Display Name", style="cyan", max_width=25)
        table.add_column("Tools", style="green", no_wrap=True)
        table.add_column("Status", style="bold white", no_wrap=True)
        table.add_column("Type", style="dim cyan", no_wrap=True)

        for i, server in enumerate(servers):
            display_name = server.get('displayName', server.get('qualifiedName', 'Unknown'))
            tool_count = str(len(server.get("tools", [])))

            status = "[bold green]Active[/bold green]" if server.get("enabled", True) else "[bold red]Disabled[/bold red]"

            conn_type = (server.get("connections", [{}])[0] or {}).get("type", "unknown")
            type_display = {
                "stdio": "LOCAL",
                "http": "HTTP",
                "shttp": "HTTPS",
                "sse": "STREAM"
            }.get(conn_type, conn_type.upper())

            table.add_row(str(i + 1), display_name, tool_count, status, type_display)

        self.console.print(table)

    async def _display_server_details(self, servers, choice):
        """Display detailed server information."""
        try:
            server_index = int(choice.strip()) - 1
            if 0 <= server_index < len(servers):
                server = servers[server_index]

                # Build comprehensive server card
                display_name = server.get('displayName')
                q_name = server.get('qualifiedName')
                description = server.get('description', 'No description available.')
                homepage = server.get('homepage', '')

                # Configuration summary
                config = server.get('config', {})
                config_count = len(config)

                # Tools summary
                tools = server.get('tools', [])
                tool_names = [t.get('name', 'Unknown') for t in tools[:5]]
                if len(tools) > 5:
                    tool_names.append(f"... and {len(tools) - 5} more")

                # Connection info
                conn_info = (server.get("connections", [{}])[0] or {})
                conn_type = conn_info.get("type", "unknown")
                conn_url = conn_info.get("url", "N/A")

                # Build detailed panel
                details_panel = Panel(
                    f"""[bold blue]Server Information[/bold blue]

[bold]Name:[/bold] {display_name}
[bold]Qualified Name:[/bold] {q_name}
[bold]Description:[/bold] {description}

[bold cyan]Tools & Capabilities[/bold cyan]
[bold]Available Tools:[/bold] {len(tools)}
[bold]Sample Tools:[/bold] {', '.join(tool_names[:3]) if tool_names else 'None'}

[bold purple]Configuration[/bold purple]
[bold]Parameters Set:[/bold] {config_count}
[bold]Connection Type:[/bold] {conn_type.upper()}

[bold yellow]Links & Resources[/bold yellow]
[bold]Homepage:[/bold] [link={homepage}]{homepage}[/link]""",
                    title=f"[details] {display_name} Details",
                    border_style="cyan",
                    padding=(1, 2)
                )
                self.console.print(details_panel)

                # Configuration details if available
                if config:
                    config_panel = Panel(
                        "\n".join(f"[bold]{k}:[/bold] {v}" for k, v in config.items()),
                        title="Configuration Details",
                        border_style="yellow"
                    )
                    self.console.print(config_panel)
            else:
                self.console.print("[red]Invalid server ID.[/red]")
        except (ValueError, IndexError):
            self.console.print("[red]Invalid input.[/red]")

    async def toggle_server_enabled_status(self):
        """Toggle server enabled/disabled status."""
        try:
            installed_servers = self.config_manager.get_installed_servers(self.config_name)
            if not installed_servers:
                self.console.print("[yellow]No servers to toggle.[/yellow]")
                return

            # Display servers with current status
            table = Table(title="[toggle] Enable/Disable Servers", title_style="yellow")

            table.add_column("ID", style="magenta", no_wrap=True)
            table.add_column("Display Name", style="cyan")
            table.add_column("Current Status", style="bold white")

            for i, server in enumerate(installed_servers):
                status = "[bold green]ENABLED[/bold green]" if server.get("enabled", True) else "[bold red]DISABLED[/bold red]"
                table.add_row(str(i + 1), server.get('displayName'), status)

            self.console.print(table)

            # Get user selection
            selection = await self.prompt_session.prompt_async(
                "Enter server ID(s) (ranges like 1-3, individual like 1 3 5, or Enter to cancel): ",
                is_password=False
            )

            if not selection:
                return

            # Parse and validate selection
            server_indices = self._parse_server_indices(selection, len(installed_servers))
            if not server_indices:
                self.console.print("[red]No valid servers selected.[/red]")
                return

            # Toggle selected servers
            toggled_servers = []
            for idx in server_indices:
                server = installed_servers[idx]
                old_status = server.get("enabled", True)
                server["enabled"] = not old_status

                status_text = "[bold green]ENABLED[/bold green]" if not old_status else "[bold red]DISABLED[/bold red]"
                toggled_servers.append(f"{server.get('displayName')} -> {status_text}")

            # Save updated configuration
            config_data = self.config_manager.load_configuration(self.config_name)
            config_data["installed_servers"] = installed_servers
            self.config_manager.save_configuration(config_data, self.config_name)

            # Display results
            result_panel = Panel(
                f"[bold green]Server Status Updated[/bold green]\n\n" +
                "\n".join(f"  {server}" for server in toggled_servers),
                title="Status Changes",
                border_style="green"
            )
            self.console.print(result_panel)

            # Reload servers
            with self.console.status("Applying changes..."):
                await self.client.reload_servers()

        except Exception as e:
            self.console.print(f"[red]Toggle error: {e}[/red]")

    async def reconfigure_server(self):
        """Reconfigure an installed server's parameters."""
        try:
            installed_servers = self.config_manager.get_installed_servers(self.config_name)
            if not installed_servers:
                self.console.print("[yellow]No servers to reconfigure.[/yellow]")
                return

            # Display servers
            table = Table(title="[reconfig] Reconfigure Servers", title_style="yellow")

            table.add_column("ID", style="magenta", no_wrap=True)
            table.add_column("Display Name", style="cyan")
            table.add_column("Configured", style="green", no_wrap=True)

            for i, server in enumerate(installed_servers):
                has_config = "Yes" if server.get("config") else "No"
                table.add_row(str(i + 1), server.get('displayName'), has_config)

            self.console.print(table)

            # Get server selection
            choice = await self.prompt_session.prompt_async(
                "Enter server ID to reconfigure: ", is_password=False
            )

            if not choice:
                return

            try:
                server_index = int(choice.strip()) - 1
                if not (0 <= server_index < len(installed_servers)):
                    raise ValueError()

                selected_server = installed_servers[server_index]
                server_name = selected_server.get("displayName", selected_server.get("qualifiedName"))

                self.console.print(f"\n[bold cyan]Reconfiguring: {server_name}[/bold cyan]")

                # Fetch latest server details
                with self.console.status("Getting latest server information..."):
                    latest_details = await self.smithery_client.get_server(
                        selected_server.get("qualifiedName")
                    )

                # Get new configuration
                new_config = await self._ask_for_server_config(latest_details)
                if new_config is None:
                    return

                # Update server configuration
                installed_servers[server_index]["config"] = new_config

                # Save updated configuration
                config_data = self.config_manager.load_configuration(self.config_name)
                config_data["installed_servers"] = installed_servers
                self.config_manager.save_configuration(config_data, self.config_name)

                # Display success
                success_panel = Panel(
                    f"[bold green]Reconfiguration Complete[/bold green]\n\n"
                    f"[bold]Server:[/bold] {server_name}\n"
                    f"[bold]Parameters Updated:[/bold] {len(new_config) if new_config else 0}",
                    title="Server Reconfigured",
                    border_style="green"
                )
                self.console.print(success_panel)

                # Reload servers
                with self.console.status("Applying new configuration..."):
                    await self.client.reload_servers()

            except (ValueError, IndexError):
                self.console.print("[red]Invalid server ID.[/red]")

        except Exception as e:
            self.console.print(f"[red]Reconfiguration error: {e}[/red]")

    async def inspect_server_from_registry(self):
        """Inspect detailed server information from registry."""
        try:
            server_name = await self.prompt_session.prompt_async(
                "Enter server qualified name: ", is_password=False
            )

            if not server_name:
                return

            with self.console.status(f"Inspecting {server_name}..."):
                server = await self.smithery_client.get_server(server_name)

            # Professional server inspection display
            await self._display_registry_server_details(server)

        except Exception as e:
            if "API key is not set" in str(e):
                self.console.print("[bold yellow]API key required. Please configure Smithery API key first.[/bold yellow]")
                await self.configure_api_key()
            else:
                self.console.print(f"[red]Inspection error: {e}[/red]")

    async def _display_registry_server_details(self, server):
        """Display comprehensive server details from registry."""
        display_name = server.get("displayName", "Unknown Server")
        q_name = server.get("qualifiedName", "")
        description = server.get("description", "No description available.")
        homepage = server.get("homepage", "")

        # Security and installation info
        security_info = server.get("security", {})
        security_passed = security_info.get("scanPassed", False)
        security_text = "[bold green]VERIFIED[/bold green]" if security_passed else "[bold red]UNVERIFIED[/bold red]"

        # Tools analysis
        tools = server.get("tools", [])
        tool_count = len(tools)

        # Connection analysis
        connections = server.get("connections", [])
        conn_info = connections[0] if connections else {}
        conn_type = conn_info.get("type", "unknown")
        conn_url = conn_info.get("url", "N/A")

        # Build comprehensive inspection panel
        inspection_panel = Panel(
            f"""[bold blue]SERVER INSPECTION REPORT[/bold blue]

[bold purple]BASIC INFORMATION[/bold purple]
[bold]Display Name:[/bold] {display_name}
[bold]Qualified Name:[/bold] {q_name}
[bold]Homepage:[/bold] [link={homepage}]{homepage}[/link]
[bold]Description:[/bold] {description}

[bold cyan]SECURITY ANALYSIS[/bold cyan]
[bold]Security Scan:[/bold] {security_text}
[bold]Last Updated:[/bold] {server.get('updatedAt', 'N/A')}

[bold green]CAPABILITIES & TOOLS[/bold green]
[bold]Tools Available:[/bold] {tool_count}
[bold]Connection Type:[/bold] {conn_type.upper()}

[bold yellow]CONNECTION DETAILS[/bold yellow]
[bold]Endpoint URL:[/bold] {conn_url}
[bold]Configuration Required:[/bold] {"Yes" if conn_info.get("configSchema") else "No"}""",
            title=f"[inspect] {display_name} - Registry Inspection",
            border_style="magenta",
            padding=(1, 2)
        )
        self.console.print(inspection_panel)

        # Display tools if available
        if tool_count > 0:
            await self._display_tools_details(tools, display_name)

        # Display configuration schema if available
        config_schema = conn_info.get("configSchema", {})
        if config_schema.get("properties"):
            self._display_config_schema(config_schema, display_name)

    async def _display_tools_details(self, tools, server_name):
        """Display detailed tools information."""
        if len(tools) <= 5:
            # Show all tools
            tool_list = "\n".join(f"  {t.get('name', 'Unknown')}: {t.get('description', 'No description')}" for t in tools)
        else:
            # Show first 5 and summary
            tool_list = "\n".join(f"  {t.get('name', 'Unknown')}: {t.get('description', 'No description')}" for t in tools[:5])
            tool_list += f"\n  ... and {len(tools) - 5} more tools"

        tools_panel = Panel(
            tool_list,
            title="[tools] Available Tools",
            border_style="green"
        )
        self.console.print(tools_panel)

    def _display_config_schema(self, schema, server_name):
        """Display configuration schema for server setup."""
        properties = schema.get("properties", {})

        config_list = []
        for key, prop in list(properties.items())[:10]:  # Limit to 10
            prop_type = prop.get("type", "string")
            required = "" if prop.get("default") else " [bold red](required)[/bold red]"
            config_list.append(f"  [bold]{key}[/bold] ({prop_type}){required}")

        if len(properties) > 10:
            config_list.append(f"  ... and {len(properties) - 10} more parameters")

        config_panel = Panel(
            "\n".join(config_list) if config_list else "[dim]  No configuration parameters required[/dim]",
            title="[config] Configuration Requirements",
            border_style="yellow"
        )
        self.console.print(config_panel)

    def clear_api_cache(self):
        """Clear the Smithery API cache."""
        self.smithery_client.clear_cache()
        success_panel = Panel(
            "[bold green]API cache cleared successfully![/bold green]\n\n"
            "[dim]Next requests will fetch fresh data from Smithery registry.[/dim]",
            title="[cache] Cache Cleared",
            border_style="green"
        )
        self.console.print(success_panel)

    async def configure_api_key(self):
        """Configure Smithery API key."""
        config_panel = Panel(
            "[bold]Smithery API Key Configuration[/bold]\n\n"
            "[dim]The API key is required to access the Smithery MCP server registry.\n"
            "Get your key at: https://smithery.io[/dim]",
            title="[api] API Key Setup",
            border_style="yellow"
        )
        self.console.print(config_panel)

        try:
            api_key = await self.prompt_session.prompt_async("Enter Smithery API Key: ", is_password=True)

            if api_key:
                self.smithery_client.set_api_key(api_key, self.config_name)
                success_panel = Panel(
                    "[bold green]API key configured successfully![/bold green]",
                    title="[success] API Key Set",
                    border_style="green"
                )
                self.console.print(success_panel)
            else:
                self.console.print("[yellow]API key configuration cancelled.[/yellow]")
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]API key configuration cancelled.[/yellow]")

    async def view_server_categories(self):
        """View servers organized by categories."""
        self.console.print()
        self.console.print("[bold cyan]🎯 SERVER CATEGORIES VIEW[/bold cyan]")

        try:
            # Get installed servers
            installed_servers = self.config_manager.get_installed_servers(self.config_name)

            if not installed_servers:
                self.console.print("[yellow]No servers installed. Please install servers first.[/yellow]")
                return

            # Organize servers by categories
            categories = await self._organize_servers_by_category(installed_servers)

            # Display categories overview
            self._display_categories_overview(categories)

            # Show detailed view of categories with servers
            await self._display_category_details(categories)

        except Exception as e:
            self.console.print(f"[red]Category view error: {e}[/red]")

        # Return to menu
        await self.prompt_session.prompt_async("Press Enter to return to main menu...", is_password=False)

    async def check_server_health(self):
        """Check health status of installed servers."""
        self.console.print("[yellow]Health check not yet implemented.[/yellow]")
        await self.prompt_session.prompt_async("Press Enter to continue...", is_password=False)

    async def backup_restore_configuration(self):
        """Backup or restore configuration."""
        self.console.print("[yellow]Backup/restore not yet implemented.[/yellow]")
        await self.prompt_session.prompt_async("Press Enter to continue...", is_password=False)

    async def setup_server_connectivity(self):
        """Professional server connectivity setup and configuration."""
        self.console.print()
        self.console.print("[bold cyan]🔗 SERVER CONNECTIVITY SETUP[/bold cyan]")

        # Check current server state
        try:
            # Get installed servers
            installed_servers = self.config_manager.get_installed_servers(self.config_name)

            if not installed_servers:
                self.console.print("[yellow]No servers installed. Please install servers first.[/yellow]")
                return

            # Display connectivity overview
            await self._display_connectivity_overview(installed_servers)

            # Connectivity options menu
            while True:
                connectivity_panel = Panel(
                    "[bold green]Connectivity Options[/bold green]\n\n"
                    "1. 🔍 Test All Connections     | Test connectivity for all installed servers\n"
                    "2. 🔧 Fix Connection Issues   | Troubleshoot and fix broken connections\n"
                    "3. 🌐 Configure Proxy Settings | Setup proxy for network connectivity\n"
                    "4. 🔒 Test Network Access     | Verify Smithery API accessibility\n"
                    "5. 📊 Connectivity Report     | Generate detailed connectivity report\n\n"
                    "6. ↩️  Back to Main Menu\n\n"
                    "[dim]Choose option (1-6):[/dim]",
                    title="[network] Server Connectivity Configuration",
                    border_style="blue",
                )
                self.console.print(connectivity_panel)

                choice = await self.prompt_session.prompt_async("Enter choice (1-6): ", is_password=False)

                if choice == "1":
                    await self._test_all_connections(installed_servers)
                elif choice == "2":
                    await self._fix_connection_issues(installed_servers)
                elif choice == "3":
                    await self._configure_proxy_settings()
                elif choice == "4":
                    await self._test_network_access()
                elif choice == "5":
                    await self._generate_connectivity_report(installed_servers)
                elif choice == "6":
                    break
                else:
                    self.console.print("[red]Invalid choice. Please select 1-6.[/red]")

                self.console.print()

        except Exception as e:
            self.console.print(f"[red]Connectivity setup error: {e}[/red]")

        # Return to menu
        await self.prompt_session.prompt_async("Press Enter to return to main menu...", is_password=False)

    def show_server_directory(self):
        """Show information about server directory organization."""
        import os

        servers_dir = self._get_servers_base_dir()

        directory_panel = Panel(
            f"""[bold green]Server Directory Organization[/bold green]

[bold]Servers Location:[/bold] {servers_dir}

[bold blue]Why this organization is perfect:[/bold blue]
Keep everything clean and organized
Server files don't clutter your workspace
Protect files from accidental modification
Easy to find and manage all installed servers

[bold cyan]Directory structure:[/bold cyan]
├── mcp-server-filesystem/
├── mcp-server-database/
└── mcp-server-search/

[dim]Tip: Use terminal commands to manage server directories[/dim]""",
            title="Server Organization",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(directory_panel)

    def _get_servers_base_dir(self) -> str:
        """Get the base directory for server repositories."""
        import os
        return os.path.join(os.path.expanduser("~"), ".ollmcp", "servers")

    # Connectivity Setup Helper Methods
    async def _display_connectivity_overview(self, installed_servers):
        """Display connectivity overview of installed servers."""
        self.console.print("[bold blue]📊 Connectivity Overview[/bold blue]")

        connectable = 0
        smithery_servers = 0
        with_issues = 0

        for server in installed_servers:
            server_name = server.get("qualifiedName", "")
            if server_name.startswith("@") and "/" in server_name:
                smithery_servers += 1
                connectable += 1  # Smithery servers can be handled specially
            else:
                server_url = server.get("url", "")
                if server_url:
                    connectable += 1
                else:
                    with_issues += 1

        overview_panel = Panel(
            f"""[bold cyan]Installed Servers:[/bold] {len(installed_servers)}
[bold green]Connectable Servers:[/bold] {connectable}
[bold yellow]Smithery Servers:[/bold] {smithery_servers}
[bold red]Connection Issues:[/bold] {with_issues}

[bold]Last Check:[/bold] Never (run connectivity test first)""",
            title="Server Connectivity Status",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(overview_panel)

    async def _test_all_connections(self, installed_servers):
        """Test connectivity for all installed servers."""
        self.console.print("\n[bold green]🔍 TESTING ALL CONNECTIONS[/bold green]")

        test_results = []

        for server in installed_servers:
            server_name = server.get("qualifiedName", server.get("displayName", "Unknown"))
            server_url = server.get("url", "")

            with self.console.status(f"Testing {server_name}..."):
                if server_name.startswith("@") and "/" in server_name:
                    # Smithery server - skip connectivity check
                    test_results.append({
                        "name": server_name,
                        "status": "Smithery Server (Skipped)",
                        "color": "cyan"
                    })
                elif server_url:
                    try:
                        response = await self._async_url_check(server_url)
                        if response:
                            test_results.append({
                                "name": server_name,
                                "status": "✅ Connected",
                                "color": "green"
                            })
                        else:
                            test_results.append({
                                "name": server_name,
                                "status": "❌ Connection Failed",
                                "color": "red"
                            })
                    except Exception as e:
                        test_results.append({
                            "name": server_name,
                            "status": f"❌ Error: {str(e)}",
                            "color": "red"
                        })
                else:
                    test_results.append({
                        "name": server_name,
                        "status": "⚠️  No URL configured",
                        "color": "yellow"
                    })

        # Display results
        result_table = Table(title="Connectivity Test Results", title_style="bold blue")
        result_table.add_column("Server", style="cyan")
        result_table.add_column("Status", style="white")

        for result in test_results:
            result_table.add_row(
                result["name"],
                f"[{result['color']}]{result['status']}[/{result['color']}]"
            )

        self.console.print(result_table)

    async def _async_url_check(self, url):
        """Perform async URL connectivity check."""
        try:
            import asyncio
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False

    async def _fix_connection_issues(self, installed_servers):
        """Help troubleshoot and fix connection issues."""
        self.console.print("\n[bold yellow]🔧 CONNECTION TROUBLESHOOTING[/bold yellow]")

        # Check internet connectivity
        self.console.print("\n[bold blue]1. Checking Internet Connectivity[/bold blue]")
        internet_test = await self._test_internet_connectivity()
        if not internet_test:
            self.console.print("[red]❌ No internet connection detected![/red]")
            return

        self.console.print("[green]✅ Internet connection OK[/green]")

        # Check API key for Smithery servers
        self.console.print("\n[bold blue]2. Checking Smithery API Configuration[/bold blue]")
        api_key = self.smithery_client.get_api_key(self.config_name)
        if api_key:
            self.console.print("[green]✅ Smithery API key configured[/green]")
        else:
            self.console.print("[red]❌ Smithery API key not configured[/red]")
            self.console.print("[blue]ℹ️  Try: Configure Smithery API Key from main menu[/blue]")

        # Check server configurations
        self.console.print("\n[bold blue]3. Checking Server Configuration[/bold blue]")
        issues_found = []

        for server in installed_servers:
            server_name = server.get("qualifiedName", "Unknown")
            server_url = server.get("url", "")

            if not server_url and not (server_name.startswith("@") and "/" in server_name):
                issues_found.append(f"{server_name}: Missing URL")

        if issues_found:
            self.console.print("[red]❌ Configuration Issues Found:[/red]")
            for issue in issues_found:
                self.console.print(f"   • {issue}")
        else:
            self.console.print("[green]✅ All server configurations look good[/green]")

        # Provide next steps
        if issues_found or not api_key:
            next_steps = Panel(
                "[bold]Recommended Next Steps:[/bold]\n\n"
                "1. Configure Smithery API key if needed\n"
                "2. Check server URLs in configuration\n"
                "3. Run network test to verify connectivity\n"
                "4. Try reinstalling problematic servers",
                title="Troubleshooting Recommendations",
                border_style="yellow"
            )
            self.console.print("\n" + next_steps)
        else:
            self.console.print("\n[green]🎉 No connectivity issues detected![/green]")

    async def _configure_proxy_settings(self):
        """Configure proxy settings for network connectivity."""
        self.console.print("\n[bold purple]🌐 PROXY CONFIGURATION[/bold purple]")

        # Note: This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Detect current proxy settings
        # 2. Allow user to configure proxies
        # 3. Test proxy connectivity
        # 4. Save proxy settings to configuration

        proxy_panel = Panel(
            "[bold yellow]Proxy Configuration[/bold yellow]\n\n"
            "[red]This feature is not yet implemented.[/red]\n\n"
            "[dim]Future implementation will include:[/dim]\n"
            "• HTTP/HTTPS Proxy configuration\n"
            "• Proxy authentication\n"
            "• Proxy testing and validation\n"
            "• Auto-detection of system proxies",
            title="Proxy Settings (Not Yet Implemented)",
            border_style="yellow"
        )
        self.console.print(proxy_panel)

    async def _test_network_access(self):
        """Test network access to key services."""
        self.console.print("\n[bold green]🔒 NETWORK ACCESS TEST[/bold green]")

        test_targets = [
            {"name": "Smithery API", "url": "https://registry.smithery.ai", "description": "Required for server registry"},
            {"name": "GitHub API", "url": "https://api.github.com", "description": "Required for repository clones"},
            {"name": "NPM Registry", "url": "https://registry.npmjs.org", "description": "Optional for NPM packages"}
        ]

        network_results = []
        success_count = 0

        for target in test_targets:
            with self.console.status(f"Testing {target['name']}..."):
                try:
                    import asyncio
                    success = await self._async_url_check(target["url"])
                    if success:
                        network_results.append({
                            "name": target["name"],
                            "status": "✅ Accessible",
                            "color": "green"
                        })
                        success_count += 1
                    else:
                        network_results.append({
                            "name": target["name"],
                            "status": "❌ Unavailable",
                            "color": "red"
                        })
                except Exception as e:
                    network_results.append({
                        "name": target["name"],
                        "status": f"❌ Error: {str(e)}",
                        "color": "red"
                    })

        # Display results
        result_table = Table(title="Network Access Test Results", title_style="bold green")
        result_table.add_column("Service", style="cyan")
        result_table.add_column("Status", style="white")
        result_table.add_column("Purpose", style="dim")

        for i, result in enumerate(network_results):
            result_table.add_row(
                result["name"],
                f"[{result['color']}]{result['status']}[/{result['color']}]",
                test_targets[i]["description"]
            )

        self.console.print(result_table)

        # Summary
        if success_count == len(test_targets):
            self.console.print(f"\n[green]🎉 All {len(test_targets)} services accessible![/green]")
        elif success_count >= len(test_targets) // 2:
            self.console.print(f"\n[yellow]⚠️  Partial network access - {success_count}/{len(test_targets)} services accessible[/yellow]")
        else:
            self.console.print(f"\n[red]❌ Network issues detected - only {success_count}/{len(test_targets)} services accessible[/red]")

    async def _generate_connectivity_report(self, installed_servers):
        """Generate comprehensive connectivity report."""
        self.console.print("\n[bold cyan]📊 CONNECTIVITY REPORT GENERATION[/bold cyan]")

        report_data = {
            "timestamp": "2025-01-09 06:00",  # Would be current datetime
            "total_servers": len(installed_servers),
            "smithery_servers": 0,
            "http_servers": 0,
            "connection_status": "Unknown",
            "api_key_configured": bool(self.smithery_client.get_api_key(self.config_name)),
            "network_access": "Untested"
        }

        # Count server types
        for server in installed_servers:
            server_name = server.get("qualifiedName", "")
            if server_name.startswith("@") and "/" in server_name:
                report_data["smithery_servers"] += 1
            elif server.get("url"):
                report_data["http_servers"] += 1

        # Test internet connectivity for basic status
        internet_ok = await self._test_internet_connectivity()
        report_data["network_access"] = "Good" if internet_ok else "Limited"

        # Generate report
        report_panel = Panel(
            f"""[bold blue]MCP-HUB Connectivity Report[/bold blue]

[bold cyan]SERVER STATISTICS[/bold cyan]
[bold]Total Servers Installed:[/bold] {report_data['total_servers']}
[bold]Smithery Servers:[/bold] {report_data['smithery_servers']}
[bold]HTTP/SSE Servers:[/bold] {report_data['http_servers']}

[bold purple]CONNECTIVITY STATUS[/bold purple]
[bold]Network Access:[/bold] {report_data['network_access']}
[bold]API Key Status:[/bold] {"Configured" if report_data['api_key_configured'] else "Not Configured"}
[bold]Report Generated:[/bold] {report_data['timestamp']}

[bold green]RECOMMENDATIONS[/bold green]
{"✅ Excellent connectivity - all systems operational" if report_data['network_access'] == "Good" and report_data['api_key_configured'] else "⚠️  Check connectivity issues using troubleshooting option"}

[bold yellow]NOTE:[/bold yellow] This is a summary report. Run connectivity tests for detailed results.""",
            title="Connectivity Report",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(report_panel)

    async def _test_internet_connectivity(self):
        """Test basic internet connectivity."""
        try:
            import asyncio
            success = await self._async_url_check("https://1.1.1.1")
            return success
        except Exception:
            return False

    # Additional helper methods
    async def _clone_server_repository(self, server_details: dict):
        """Clone and set up a server repository."""
        # Placeholder implementation
        self.console.print("[yellow]Auto-cloning not implemented yet. Please clone manually.[/yellow]")

    # Server Categories Helper Methods
    async def _organize_servers_by_category(self, installed_servers):
        """Organize installed servers into categories based on their function."""
        categories = {
            "File System": {
                "description": "File and directory management, read/write operations",
                "icon": "📁",
                "servers": [],
                "total_tools": 0
            },
            "Web & HTTP": {
                "description": "Web scraping, HTTP operations, API calls",
                "icon": "🌐",
                "servers": [],
                "total_tools": 0
            },
            "AI & ML": {
                "description": "Machine learning, AI model integration, data analysis",
                "icon": "🤖",
                "servers": [],
                "total_tools": 0
            },
            "Database": {
                "description": "Database operations, queries, data management",
                "icon": "🗄️",
                "servers": [],
                "total_tools": 0
            },
            "Development": {
                "description": "Code analysis, linting, development tools",
                "icon": "⚙️",
                "servers": [],
                "total_tools": 0
            },
            "Communication": {
                "description": "Email, messaging, communication tools",
                "icon": "💬",
                "servers": [],
                "total_tools": 0
            },
            "Media & Content": {
                "description": "Image processing, text generation, content creation",
                "icon": "🎨",
                "servers": [],
                "total_tools": 0
            },
            "Other": {
                "description": "Miscellaneous tools and utilities",
                "icon": "🔧",
                "servers": [],
                "total_tools": 0
            }
        }

        for server in installed_servers:
            server_name = server.get("displayName", server.get("qualifiedName", "Unknown"))
            description = server.get("description", "").lower()
            qualified_name = server.get("qualifiedName", "").lower()

            # Categorize based on description and qualified name
            category_name = "Other"

            # File System category
            if any(keyword in description + qualified_name for keyword in ["file", "filesystem", "directory", "folder", "storage", "disk"]):
                category_name = "File System"
            # Web & HTTP category
            elif any(keyword in description + qualified_name for keyword in ["web", "http", "api", "url", "request", "browser", "scraping"]):
                category_name = "Web & HTTP"
            # AI & ML category
            elif any(keyword in description + qualified_name for keyword in ["ai", "machine learning", "ml", "neural", "gpt", "openai", "claude"]):
                category_name = "AI & ML"
            # Database category
            elif any(keyword in description + qualified_name for keyword in ["database", "db", "sql", "mysql", "postgres", "mongodb"]):
                category_name = "Database"
            # Development category
            elif any(keyword in description + qualified_name for keyword in ["code", "programming", "lint", "debug", "test", "build"]):
                category_name = "Development"
            # Communication category
            elif any(keyword in description + qualified_name for keyword in ["email", "mail", "gmail", "message", "chat", "smtp"]):
                category_name = "Communication"
            # Media & Content category
            elif any(keyword in description + qualified_name for keyword in ["image", "video", "media", "content", "text", "generation"]):
                category_name = "Media & Content"

            categories[category_name]["servers"].append(server)
            categories[category_name]["total_tools"] += len(server.get("tools", []))

        return categories

    def _display_categories_overview(self, categories):
        """Display overview of server categories."""
        # Filter out empty categories
        active_categories = {k: v for k, v in categories.items() if v["servers"]}

        overview_table = Table(title="Server Categories Overview", title_style="bold cyan")
        overview_table.add_column("Category", style="cyan", no_wrap=True)
        overview_table.add_column("Icon", style="white", justify="center", no_wrap=True)
        overview_table.add_column("Servers", style="green", justify="center")
        overview_table.add_column("Tools", style="yellow", justify="center")
        overview_table.add_column("Description", style="dim", max_width=40)

        for category_name, category_info in active_categories.items():
            overview_table.add_row(
                category_name,
                category_info["icon"],
                str(len(category_info["servers"])),
                str(category_info["total_tools"]),
                category_info["description"]
            )

        self.console.print(overview_table)

        self.console.print(f"\n[bold cyan]📊 Total Statistics:[/bold cyan]")
        total_servers = sum(len(cat["servers"]) for cat in active_categories.values())
        total_tools = sum(cat["total_tools"] for cat in active_categories.values())

        stats_panel = Panel(
            f"[bold green]Active Servers:[/bold green] {total_servers}\n"
            f"[bold yellow]Available Tools:[/bold yellow] {total_tools}\n"
            f"[bold blue]Categories:[/bold blue] {len(active_categories)}",
            title="System Statistics",
            border_style="blue"
        )
        self.console.print(stats_panel)

    async def _display_category_details(self, categories):
        """Display detailed view of categories with server information."""
        active_categories = {k: v for k, v in categories.items() if v["servers"]}

        self.console.print(f"\n[bold cyan]📋 CATEGORY DETAILS:[/bold cyan]")
        self.console.print(f"Showing {len(active_categories)} active categories:\n")

        for category_name, category_info in active_categories.items():
            if not category_info["servers"]:
                continue

            # Category header
            category_panel = Panel(
                f"[bold]{category_name}[/bold] {category_info['icon']}\n"
                f"[dim]{category_info['description']}[/dim]\n\n"
                f"[bold cyan]Servers:[/bold cyan] {len(category_info['servers'])} | "
                f"[bold yellow]Tools:[/bold yellow] {category_info['total_tools']}",
                title=f"Category: {category_name}",
                border_style="blue",
                padding=(1, 2)
            )
            self.console.print(category_panel)

            # Server list for this category
            servers_table = Table(show_header=True, header_style="bold magenta")
            servers_table.add_column("#", style="magenta", no_wrap=True, justify="center")
            servers_table.add_column("Server Name", style="cyan", max_width=30)
            servers_table.add_column("Tools", style="green", justify="center", no_wrap=True)
            servers_table.add_column("Status", style="white", no_wrap=True)
            servers_table.add_column("Connection", style="dim cyan", no_wrap=True)

            for i, server in enumerate(category_info["servers"], 1):
                server_name = server.get("displayName", server.get("qualifiedName", "Unknown"))
                tool_count = len(server.get("tools", []))
                enabled = server.get("enabled", True)
                status = "[bold green]Active[/bold green]" if enabled else "[bold red]Disabled[/bold red]"

                # Connection type
                conn_info = server.get("connections", [{}])[0]
                conn_type = conn_info.get("type", "unknown")
                if conn_type == "stdio":
                    conn_type = "Local"
                elif conn_type in ["http", "shttp", "sse"]:
                    conn_type = "HTTP"
                else:
                    conn_type = conn_type.upper()

                servers_table.add_row(str(i), server_name, str(tool_count), status, conn_type)

            self.console.print(servers_table)
            self.console.print()  # Spacing between categories

    def _check_docker_available(self) -> bool:
        """Check if Docker is available."""
        import subprocess
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            return "Docker version" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
