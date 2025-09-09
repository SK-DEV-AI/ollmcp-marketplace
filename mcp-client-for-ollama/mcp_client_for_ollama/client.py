"""MCP Client for Ollama - A TUI client for interacting with Ollama models and MCP servers"""
import asyncio
import os
from contextlib import AsyncExitStack
from typing import List, Optional

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
import ollama

from . import __version__
from .config.manager import ConfigManager
from .utils.version import check_for_updates
from .utils.constants import DEFAULT_CLAUDE_CONFIG, DEFAULT_MODEL, DEFAULT_OLLAMA_HOST, DEFAULT_COMPLETION_STYLE
from .server.connector import ServerConnector
from .models.manager import ModelManager
from .models.config_manager import ModelConfigManager
from .tools.manager import ToolManager
from .utils.streaming import StreamingManager
from .utils.tool_display import ToolDisplayManager
from .utils.hil_manager import HumanInTheLoopManager
from .utils.fzf_style_completion import FZFStyleCompleter
from .mcphub.mcphub_manager import MCPHubManager
from .mcphub.smithery_client import SmitheryClient


class MCPClient:
    """Main client class for interacting with Ollama and MCP servers"""

    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_OLLAMA_HOST):
        self.exit_stack = AsyncExitStack()
        self.ollama = ollama.AsyncClient(host=host)
        self.console = Console()
        self.config_manager = ConfigManager(self.console)
        self.smithery_client = SmitheryClient()
        self.server_connector = ServerConnector(self.exit_stack, self.console)
        self.model_manager = ModelManager(console=self.console, default_model=model, ollama=self.ollama)
        self.model_config_manager = ModelConfigManager(console=self.console)
        self.tool_manager = ToolManager(console=self.console, server_connector=self.server_connector)
        self.streaming_manager = StreamingManager(console=self.console)
        self.tool_display_manager = ToolDisplayManager(console=self.console)
        self.hil_manager = HumanInTheLoopManager(console=self.console)
        self.sessions = {}
        self.chat_history = []
        self.prompt_session = PromptSession(completer=FZFStyleCompleter(), style=Style.from_dict(DEFAULT_COMPLETION_STYLE))
        self.retain_context = True
        self.actual_token_count = 0
        self.thinking_mode = True
        self.show_thinking = False
        self.show_tool_execution = True
        self.show_metrics = False
        self.default_configuration_status = False
        self.current_config_name = "default"
        self.server_connection_params = {}

    async def connect_to_servers(self, server_paths=None, server_urls=None, config_paths=None, auto_discovery=False):
        self.server_connection_params = {
            'server_paths': server_paths,
            'server_urls': server_urls,
            'config_paths': config_paths,
            'auto_discovery': auto_discovery
        }
        sessions, available_tools, enabled_tools = await self.server_connector.connect_to_servers(
            server_paths=server_paths,
            server_urls=server_urls,
            config_paths=config_paths,
            auto_discovery=auto_discovery
        )
        self.sessions = sessions
        self.tool_manager.set_available_tools(available_tools)
        self.tool_manager.set_enabled_tools(enabled_tools)

    async def chat_loop(self):
        self.clear_console()
        self.console.print(Panel(Text.from_markup("[bold green]Welcome to the MCP Client for Ollama 🦙[/bold green]", justify="center"), expand=True, border_style="green"))
        self.display_available_tools()
        self.display_current_model()
        self.print_help()
        self.print_auto_load_default_config_status()
        await self.display_check_for_updates()

        while True:
            try:
                query = await self.get_user_input()
                if query.lower() in ['mcphub', 'hub', 'mcp-hub']:
                    mcphub_manager = MCPHubManager(self.console, self.smithery_client, self.config_manager, self, self.current_config_name)
                    await mcphub_manager.run()
                    self.clear_console()
                    self.display_available_tools()
                    self.display_current_model()
                    self.print_help()
                    continue
                # ... other commands ...
                if query.lower() in ['quit', 'q', 'exit', 'bye']:
                    break
            except Exception as e:
                self.console.print(Panel(f"[bold red]Error:[/bold red] {str(e)}", title="Exception", border_style="red", expand=False))

    # ... all other methods of MCPClient ...
    def display_current_model(self): self.model_manager.display_current_model()
    async def supports_thinking_mode(self): return False
    async def select_model(self): pass
    def clear_console(self): os.system('cls' if os.name == 'nt' else 'clear')
    def display_available_tools(self): self.tool_manager.display_available_tools()
    def select_tools(self): pass
    def configure_model_options(self): pass
    def _display_chat_history(self): pass
    async def process_query(self, query: str): return ""
    async def get_user_input(self, prompt_text: str = None): return await self.prompt_session.prompt_async(f"{prompt_text or ''}❯ ")
    async def display_check_for_updates(self): pass
    def print_help(self): self.console.print("Help text...")
    def print_auto_load_default_config_status(self): pass
    def toggle_context_retention(self): pass
    async def toggle_thinking_mode(self): pass
    async def toggle_show_thinking(self): pass
    def toggle_show_tool_execution(self): pass
    def toggle_show_metrics(self): pass
    def clear_context(self): pass
    def display_context_stats(self): pass
    def auto_load_default_config(self): pass
    def save_configuration(self, config_name=None): pass
    def load_configuration(self, config_name=None): self.current_config_name = config_name; return True
    def reset_configuration(self): self.current_config_name = "default"; return True
    async def cleanup(self): await self.exit_stack.aclose()
    async def reload_servers(self):
        await self.server_connector.disconnect_all_servers()
        self.exit_stack = self.server_connector.exit_stack
        await self.connect_to_servers(**self.server_connection_params)
        self.display_available_tools()


app = typer.Typer(help="MCP Client for Ollama", context_settings={"help_option_names": ["-h", "--help"]})

@app.command()
def main(
    # ... (typer options) ...
    mcp_server: Optional[List[str]] = typer.Option(None, "--mcp-server", "-s"),
    mcp_server_url: Optional[List[str]] = typer.Option(None, "--mcp-server-url", "-u"),
    servers_json: Optional[str] = typer.Option(None, "--servers-json", "-j"),
    auto_discovery: bool = typer.Option(False, "--auto-discovery", "-a"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m"),
    host: str = typer.Option(DEFAULT_OLLAMA_HOST, "--host", "-H"),
    version: Optional[bool] = typer.Option(None, "--version", "-v"),
):
    if version:
        typer.echo(f"mcp-client-for-ollama {__version__}"); raise typer.Exit()

    asyncio.run(async_main(mcp_server, mcp_server_url, servers_json, auto_discovery, model, host))

async def async_main(mcp_server, mcp_server_url, servers_json, auto_discovery, model, host):
    console = Console()
    client = MCPClient(model=model, host=host)

    # ... (check if ollama is running) ...

    config_paths = []
    if servers_json:
        if os.path.exists(servers_json):
            config_paths.append(servers_json)
        else:
            console.print(f"[bold red]Error: Specified JSON config file not found: {servers_json}[/bold red]"); return

    from .mcphub.hub_config_manager import MCPHubConfigManager
    hub_config_path = MCPHubConfigManager().get_config_path()
    if os.path.exists(hub_config_path):
        config_paths.append(hub_config_path)

    auto_discovery_final = auto_discovery
    if not (mcp_server or mcp_server_url or config_paths or auto_discovery):
        if os.path.exists(DEFAULT_CLAUDE_CONFIG):
            auto_discovery_final = True

    try:
        await client.connect_to_servers(mcp_server, mcp_server_url, config_paths, auto_discovery_final)
        client.auto_load_default_config()
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    app()
