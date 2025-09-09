import pytest
import respx
import os
from unittest.mock import MagicMock, AsyncMock, patch

from mcp_client_for_ollama.mcphub.smithery_client import SmitheryClient
from mcp_client_for_ollama.mcphub.mcphub_manager import MCPHubManager


# --- Tests for SmitheryClient ---

@pytest.fixture
def smithery_client():
    """Fixture for a stateless SmitheryClient instance."""
    return SmitheryClient()

@pytest.mark.asyncio
@respx.mock
async def test_get_server_success(smithery_client):
    """Test successfully fetching a server."""
    server_id = "test/server"
    api_key = "test_key"
    mock_response = {"qualifiedName": server_id, "description": "A test server."}
    respx.get(f"{smithery_client.base_url}/servers/{server_id}").respond(200, json=mock_response)

    response = await smithery_client.get_server(server_id, api_key)
    assert response == mock_response
    assert respx.calls.call_count == 1
    assert respx.calls.last.request.headers["authorization"] == f"Bearer {api_key}"

@pytest.mark.asyncio
@respx.mock
async def test_get_server_caching(smithery_client):
    """Test that get_server caches responses."""
    server_id = "test/cached-server"
    api_key = "test_key"
    mock_response = {"qualifiedName": server_id, "description": "A cached server."}
    respx.get(f"{smithery_client.base_url}/servers/{server_id}").respond(200, json=mock_response)

    # First call - should hit the API
    await smithery_client.get_server(server_id, api_key)
    assert respx.calls.call_count == 1
    assert server_id in smithery_client.server_cache

    # Second call - should use the cache
    await smithery_client.get_server(server_id, api_key)
    assert respx.calls.call_count == 1  # API should not be called again

def test_clear_cache(smithery_client):
    """Test clearing the cache."""
    smithery_client.server_cache = {"test/server": {"data": "old"}}
    assert smithery_client.server_cache
    smithery_client.clear_cache()
    assert not smithery_client.server_cache

@pytest.mark.asyncio
@respx.mock
async def test_search_servers_success(smithery_client):
    """Test successfully searching for servers."""
    query = "filesystem"
    api_key = "test_key"
    mock_response = {"servers": [{"qualifiedName": "test/fs"}]}
    respx.get(f"{smithery_client.base_url}/servers").respond(200, json=mock_response)

    response = await smithery_client.search_servers(query, api_key)
    assert response == mock_response
    assert respx.calls.last.request.url.query.decode() == "q=filesystem&page=1&pageSize=10"

@pytest.mark.asyncio
async def test_get_server_no_api_key(smithery_client):
    """Test that methods raise ValueError if the API key is not provided."""
    with pytest.raises(ValueError, match="API key is required"):
        await smithery_client.get_server("test/server", api_key="")
    with pytest.raises(ValueError, match="API key is required"):
        await smithery_client.search_servers("query", api_key="")


# --- Tests for MCPHubManager ---

@pytest.fixture
def mock_console():
    return MagicMock()

@pytest.fixture
def mock_smithery_client():
    return AsyncMock(spec=SmitheryClient)

@pytest.fixture
def mock_main_config_manager():
    mock = MagicMock()
    mock.load_configuration.return_value = {"smithery_api_key": "test_api_key_123"}
    return mock

@pytest.fixture
def mock_hub_config_manager():
    return MagicMock()

@pytest.fixture
def mock_main_client():
    return AsyncMock()

@pytest.fixture
def hub_manager(mock_console, mock_smithery_client, mock_main_config_manager, mock_main_client, mock_hub_config_manager):
    """Fixture for an MCPHubManager instance with mocked dependencies."""
    manager = MCPHubManager(
        console=mock_console,
        smithery_client=mock_smithery_client,
        main_config_manager=mock_main_config_manager,
        client=mock_main_client,
        config_name="default"
    )
    # Replace the real HubConfigManager with our mock
    manager.hub_config_manager = mock_hub_config_manager
    # Patch the prompt session to avoid actual user input
    manager.prompt_session = AsyncMock()
    return manager

@pytest.mark.asyncio
async def test_add_server_stdio_happy_path(hub_manager, mock_hub_config_manager, mock_main_client):
    """Test the happy path for adding a stdio server."""
    server_details = {
        "qualifiedName": "test/stdio-server",
        "homepage": "http://github.com/test/stdio",
        "connections": [{"type": "stdio", "configSchema": {"properties": {}}}]
    }
    valid_path = "/fake/path/run.py"

    # Mocks
    mock_hub_config_manager.get_servers.return_value = {}  # Not installed yet
    hub_manager.prompt_session.prompt_async.return_value = valid_path

    # Patch os.path.exists and os.path.isfile to simulate a valid file path
    with patch('os.path.exists', return_value=True), \
         patch('os.path.isfile', return_value=True):

        await hub_manager.add_server(server_details)

    # Assertions
    mock_hub_config_manager.add_server.assert_called_once()
    saved_name, saved_config = mock_hub_config_manager.add_server.call_args[0]

    assert saved_name == "test/stdio-server"
    assert saved_config["command"] == "python"
    assert saved_config["args"] == [valid_path]

    hub_manager.console.print.assert_any_call("[green]Server 'test/stdio-server' added to mcp.json.[/green]")
    mock_main_client.reload_servers.assert_called_once()

@pytest.mark.asyncio
async def test_add_server_stdio_invalid_path_then_quit(hub_manager):
    """Test entering an invalid path for stdio server, then quitting."""
    server_details = {
        "qualifiedName": "test/stdio-server",
        "homepage": "http://github.com/test/stdio",
        "connections": [{"type": "stdio"}]
    }
    # First prompt returns bad path, second returns 'q'
    hub_manager.prompt_session.prompt_async.side_effect = ["/bad/path", "q"]

    with patch('os.path.exists', return_value=False):
        await hub_manager.add_server(server_details)

    # Assertions
    assert hub_manager.prompt_session.prompt_async.call_count == 2
    hub_manager.console.print.assert_any_call("[red]Path not found: /bad/path. Please try again.[/red]")
    hub_manager.console.print.assert_any_call("[yellow]Add server operation cancelled.[/yellow]")

@pytest.mark.asyncio
async def test_add_server_already_installed(hub_manager, mock_hub_config_manager):
    """Test that adding an already installed server is handled gracefully."""
    server_name = "test/existing-server"
    server_details = {"qualifiedName": server_name}
    mock_hub_config_manager.get_servers.return_value = {server_name: {}}

    await hub_manager.add_server(server_details)

    hub_manager.console.print.assert_called_with(f"[yellow]Server '{server_name}' is already added.[/yellow]")
    mock_hub_config_manager.add_server.assert_not_called()

@pytest.mark.asyncio
async def test_uninstall_server_happy_path(hub_manager, mock_hub_config_manager, mock_main_client):
    """Test successful uninstallation."""
    server_name = "test/to-uninstall"
    mock_hub_config_manager.get_servers.return_value = {server_name: {"type": "http"}}
    # User chooses the first (and only) server
    hub_manager.prompt_session.prompt_async.return_value = "1"

    await hub_manager.uninstall_server()

    mock_hub_config_manager.remove_server.assert_called_once_with(server_name)
    hub_manager.console.print.assert_called_with(f"[green]Server '{server_name}' removed.[/green]")
    mock_main_client.reload_servers.assert_called_once()

@pytest.mark.asyncio
async def test_toggle_server_status(hub_manager, mock_hub_config_manager, mock_main_client):
    """Test toggling a server from enabled to disabled."""
    server_name = "test/toggle-me"
    server_config = {"type": "http", "disabled": False}
    mock_hub_config_manager.get_servers.return_value = {server_name: server_config}
    hub_manager.prompt_session.prompt_async.return_value = "1"

    await hub_manager.toggle_server_enabled_status()

    # The config should now be disabled
    expected_config = {"type": "http", "disabled": True}
    mock_hub_config_manager.add_server.assert_called_once_with(server_name, expected_config)
    hub_manager.console.print.assert_called_with("Server 'test/toggle-me' is now Disabled.")
    mock_main_client.reload_servers.assert_called_once()
