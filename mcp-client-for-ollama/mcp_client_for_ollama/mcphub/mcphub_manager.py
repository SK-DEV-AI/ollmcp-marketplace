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
from typing import Optional

from .smithery_client import SmitheryClient
from ..config.manager import ConfigManager


class MCPHubManager:
    """Professional MCP Server Management with Enterprise Features."""

    def __init__(
        self,
        console: Console,
        smithery_client: SmitheryClient,
        config_manager: ConfigManager,
        client,
        config_name: str,
        prompt_session: Optional[PromptSession] = None,
    ):
        self.console = console
        self.smithery_client = smithery_client
        self.config_manager = config_manager
        self.client = client
        self.config_name = config_name
        self.prompt_session = prompt_session or PromptSession()

        # Initialize API key from configuration
        self._initialize_api_key()

    def _initialize_api_key(self):
        """Initialize Smithery API key from current configuration."""
        api_key = self.smithery_client.get_api_key()
        if api_key is None:
            config_data = self.config_manager.load_configuration(self.config_name)
            api_key = config_data.get("smithery_api_key")
            if api_key:
                self.smithery_client.set_api_key(api_key)
        elif not api_key:  # If API key is empty string, try to get it from config
            config_data = self.config_manager.load_configuration(self.config_name)
            api_key = config_data.get("smithery_api_key")
            if api_key:
                self.smithery_client.set_api_key(api_key)

    async def _organize_servers_by_category(self, servers):
        """Organize servers into categories by their functionality."""
        categories = {
            "File System": {
                "servers": [],
                "icon": "📁",
                "description": "File management, directory operations, storage utilities",
                "total_tools": 0
            },
            "Web & HTTP": {
                "servers": [],
                "icon": "🌐",
                "description": "HTTP clients, web APIs, network utilities, scraping tools",
                "total_tools": 0
            },
            "AI & ML": {
                "servers": [],
                "icon": "🤖",
                "description": "AI assistance, machine learning, text processing, language models",
                "total_tools": 0
            },
            "Database": {
                "servers": [],
                "icon": "🗄️",
                "description": "Database interactions, SQL queries, data persistence",
                "total_tools": 0
            },
            "Development": {
                "servers": [],
                "icon": "💻",
                "description": "Code analysis, testing, building, development tools",
                "total_tools": 0
            },
            "Communication": {
                "servers": [],
                "icon": "💬",
                "description": "Email, messaging, notification systems, social platforms",
                "total_tools": 0
            },
            "Media & Content": {
                "servers": [],
                "icon": "🎬",
                "description": "Image processing, video editing, content creation",
                "total_tools": 0
            },
        }

        for server in servers:
            display_name = server.get("displayName", "")
            qualified_name = server.get("qualifiedName", "")
            description = server.get("description", "").lower()

            # Categorization logic based on keywords and server information
            if any(
                keyword in description + qualified_name
                for keyword in [
                    "filesystem",
                    "directory",
                    "folder",
                    "storage",
                    "disk",
                    "file",
                    "fs",
                ]
            ):
                category_name = "File System"
            # Web & HTTP category
            elif any(
                keyword in description + qualified_name
                for keyword in [
                    "web",
                    "http",
                    "api",
                    "url",
                    "request",
                    "browser",
                    "scraping",
                ]
            ):
                category_name = "Web & HTTP"
            # AI & ML category
            elif any(
                keyword in description + qualified_name
                for keyword in [
                    "ai",
                    "machine learning",
                    "ml",
                    "neural",
                    "gpt",
                    "openai",
                    "claude",
                    "anthropic",
                    "assistant",
                    "chat",
                    "text",
                    "language",
                    "nlp",
                ]
            ):
                category_name = "AI & ML"
            # Database category
            elif any(
                keyword in description + qualified_name
                for keyword in [
                    "database",
                    "db",
                    "sql",
                    "mysql",
                    "postgres",
                    "postgresql",
                    "mongodb",
                    "sqlite",
                    "redis",
                ]
            ):
                category_name = "Database"
            # Development category
            elif any(
                keyword in description + qualified_name
                for keyword in ["code", "programming", "lint", "debug", "test", "build"]
            ):
                category_name = "Development"
            # Communication category
            elif any(
                keyword in description + qualified_name
                for keyword in ["email", "mail", "gmail", "message", "chat", "smtp"]
            ):
                category_name = "Communication"
            # Media & Content category
            elif any(
                keyword in description + qualified_name
                for keyword in [
                    "image",
                    "video",
                    "media",
                    "content",
                    "text",
                    "generation",
                ]
            ):
                category_name = "Media & Content"

            categories[category_name]["servers"].append(server)
            categories[category_name]["total_tools"] += len(server.get("tools", []))

        return categories

    def _check_docker_available(self) -> bool:
        """Check if Docker is available."""
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, check=True
            )
            return "Docker version" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    # Main interface methods
    async def run(self):
        """Main MCP-HUB interface loop."""
        welcome_message = Panel(
            Text(
                "Welcome to MCP-HUB - Professional MCP Server Manager!",
                justify="center",
            ),
            border_style="green",
        )
        self.console.print(welcome_message)

        while True:
            try:
                self.display_menu()
                choice = await self.prompt_session.prompt_async(
                    "Select option: ", is_password=False
                )

                await self._handle_menu_choice(choice)
                if choice in ["14", "q", "quit"]:
                    break

            except (KeyboardInterrupt, EOFError):
                self.console.print(
                    "\n[yellow]Operation cancelled. Back to menu.[/yellow]"
                )
                continue
            except Exception as e:
                self.console.print(f"[red]Unexpected error: {e}[/red]")
                continue

    # Additional core methods would be implemented here
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
            padding=(1, 2),
        )
        self.console.print(menu_panel)

    async def _handle_menu_choice(self, choice: str):
        """Route menu choices to appropriate methods."""
        choice = choice.strip().lower()

        menu_actions = {
            "1": self.search_servers,
            "2": self.view_server_categories,
            "11": self.configure_api_key,
            "12": lambda: self.clear_api_cache(),
        }

        if choice in menu_actions:
            try:
                await menu_actions[choice]()
                if choice in ["12"]:
                    await self.prompt_session.prompt_async(
                        "Press Enter to continue...", is_password=False
                    )
            except Exception as e:
                self.console.print(f"[red]Error executing option {choice}: {e}[/red]")
        elif choice in ["14", "q", "quit"]:
            pass
        else:
            self.console.print("[red]Invalid option. Please select 1-14.[/red]")

    # Placeholder implementations for main methods
    async def search_servers(self):
        """Search and install servers with advanced features."""
        self.console.print("[yellow]Search functionality not yet implemented.[/yellow]")
        await self.prompt_session.prompt_async(
            "Press Enter to continue...", is_password=False
        )

    async def view_server_categories(self):
        """View servers organized by categories."""
        self.console.print("[yellow]Category view not yet implemented.[/yellow]")
        await self.prompt_session.prompt_async(
            "Press Enter to return to main menu...", is_password=False
        )

    async def configure_api_key(self):
        """Configure Smithery API key."""
        api_config_panel = Panel(
            "[bold]Smithery API Key Configuration[/bold]\n\n"
            "[dim]The API key is required to access the Smithery MCP server registry.\n"
            "Get your key at: https://smithery.io[/dim]",
            title="[api] API Key Setup",
            border_style="yellow",
        )
        self.console.print(api_config_panel)

        try:
            api_key = await self.prompt_session.prompt_async(
                "Enter Smithery API Key: ", is_password=True
            )

            if api_key:
                self.smithery_client.set_api_key(api_key)
                success_panel = Panel(
                    "[bold green]API key configured successfully![/bold green]",
                    title="[success] API Key Set",
                    border_style="green",
                )
                self.console.print(success_panel)
            else:
                self.console.print("[yellow]API key configuration cancelled.[/yellow]")
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]API key configuration cancelled.[/yellow]")

    def clear_api_cache(self):
        """Clear the Smithery API cache."""
        self.smithery_client.clear_cache()
        cache_panel = Panel(
            "[bold green]API cache cleared successfully![/bold green]\n\n"
            "[dim]Next requests will fetch fresh data from Smithery registry.[/dim]",
            title="[cache] Cache Cleared",
            border_style="green",
        )
        self.console.print(cache_panel)
