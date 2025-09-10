import pytest
import respx
from unittest.mock import MagicMock, AsyncMock

from mcp_client_for_ollama.mcphub.smithery_client import SmitheryClient

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_config_manager():
    """Fixture for a mocked ConfigManager."""
    mock = MagicMock()
    # Simulate a config dictionary
    mock.load_configuration.return_value = {"smithery_api_key": "test_api_key_123"}
    return mock


@pytest.fixture
def smithery_client(mock_config_manager):
    """Fixture for a SmitheryClient instance with a mocked ConfigManager."""
    return SmitheryClient(config_manager=mock_config_manager, config_name="default")


def test_smithery_client_initialization(smithery_client, mock_config_manager):
    """Test that the SmitheryClient initializes correctly."""
    mock_config_manager.load_configuration.assert_called_once_with("default")
    assert smithery_client.api_key == "test_api_key_123"
    assert smithery_client.config_name == "default"


@respx.mock
async def test_get_server_success(smithery_client):
    """Test successfully fetching a server."""
    server_id = "test/server"
    mock_response = {"qualifiedName": server_id, "description": "A test server."}
    respx.get(f"{smithery_client.base_url}/servers/{server_id}").respond(
        200, json=mock_response
    )

    response = await smithery_client.get_server(server_id)
    assert response == mock_response
    assert respx.calls.call_count == 1


@respx.mock
async def test_get_server_caching(smithery_client):
    """Test that get_server caches responses."""
    server_id = "test/cached-server"
    mock_response = {"qualifiedName": server_id, "description": "A cached server."}
    respx.get(f"{smithery_client.base_url}/servers/{server_id}").respond(
        200, json=mock_response
    )

    # First call - should hit the API
    response1 = await smithery_client.get_server(server_id)
    assert response1 == mock_response
    assert respx.calls.call_count == 1
    assert server_id in smithery_client.server_cache

    # Second call - should use the cache
    response2 = await smithery_client.get_server(server_id)
    assert response2 == mock_response
    assert respx.calls.call_count == 1  # API should not be called again


def test_clear_cache(smithery_client):
    """Test clearing the cache."""
    smithery_client.server_cache = {"test/server": {"data": "old"}}
    assert smithery_client.server_cache
    smithery_client.clear_cache()
    assert not smithery_client.server_cache


@respx.mock
async def test_search_servers_success(smithery_client):
    """Test successfully searching for servers."""
    query = "filesystem"
    mock_response = {"servers": [{"qualifiedName": "test/fs"}]}
    respx.get(f"{smithery_client.base_url}/servers").respond(200, json=mock_response)

    response = await smithery_client.search_servers(query)
    assert response == mock_response
    assert respx.calls.call_count == 1
    # Check that the query parameter was passed correctly
    assert (
        respx.calls.last.request.url.query.decode() == "q=filesystem&page=1&pageSize=10"
    )


async def test_get_server_no_api_key(mock_config_manager):
    """Test that get_server raises ValueError if the API key is not set."""
    # Simulate a config without an API key
    mock_config_manager.load_configuration.return_value = {}
    client_no_key = SmitheryClient(
        config_manager=mock_config_manager, config_name="default"
    )

    with pytest.raises(ValueError, match="API key is not set"):
        await client_no_key.get_server("test/server")


def test_set_api_key(smithery_client, mock_config_manager):
    """Test setting a new API key."""
    new_key = "new_key_456"

    # The config that will be "loaded" and then modified
    current_config = {"smithery_api_key": "test_api_key_123"}
    mock_config_manager.load_configuration.return_value = current_config

    smithery_client.set_api_key(new_key)

    # Verify that the config was loaded, modified, and saved
    mock_config_manager.load_configuration.assert_called_with("default")

    # The first argument of the first call to save_configuration
    saved_config = mock_config_manager.save_configuration.call_args[0][0]
    saved_config_name = mock_config_manager.save_configuration.call_args[0][1]

    assert saved_config["smithery_api_key"] == new_key
    assert saved_config_name == "default"

    # Verify the instance variable is also updated
    assert smithery_client.api_key == new_key


# --- Tests for MCPHubManager ---


@pytest.fixture
def mock_console():
    return MagicMock()


@pytest.fixture
def mock_prompt_session():
    # Use AsyncMock for async methods like prompt_async
    return AsyncMock()


@pytest.fixture
def mock_smithery_client():
    return AsyncMock()


@pytest.fixture
def mock_main_client():
    # Mock the main MCPClient
    return AsyncMock()


@pytest.fixture
def hub_manager(
    mock_console,
    mock_prompt_session,
    mock_smithery_client,
    mock_config_manager,
    mock_main_client,
):
    """Fixture for an MCPHubManager instance with mocked dependencies."""
    from mcp_client_for_ollama.mcphub.mcphub_manager import MCPHubManager

    return MCPHubManager(
        console=mock_console,
        smithery_client=mock_smithery_client,
        config_manager=mock_config_manager,
        client=mock_main_client,
        config_name="default",
        prompt_session=mock_prompt_session,
    )


async def test_install_server_happy_path(
    hub_manager,
    mock_prompt_session,
    mock_smithery_client,
    mock_config_manager,
    mock_main_client,
):
    """Test the successful installation of a new server."""
    # Arrange
    server_name = "test/new-server"
    mock_prompt_session.prompt_async.side_effect = [server_name]

    mock_config_manager.get_installed_servers.return_value = (
        []
    )  # No servers installed yet

    mock_server_details = {
        "qualifiedName": server_name,
        "displayName": "Test Server",
        "description": "A server for testing.",
        "security": {"scanPassed": True},
        "connections": [
            {"type": "shttp", "configSchema": {"properties": {}}}
        ],  # No config needed
    }
    mock_smithery_client.get_server.return_value = mock_server_details

    # Act
    await hub_manager.install_server()

    # Assert
    # 1. Checked if server was already installed
    mock_config_manager.get_installed_servers.assert_called_once_with("default")
    # 2. Fetched server details
    mock_smithery_client.get_server.assert_called_once_with(server_name)
    # 3. Added the new server to config
    mock_config_manager.add_installed_server.assert_called_once()
    # 4. The saved data should include the details, plus config and enabled status
    saved_data = mock_config_manager.add_installed_server.call_args[0][0]
    assert saved_data["qualifiedName"] == server_name
    assert saved_data["enabled"] is True
    assert "config" in saved_data
    # 5. Reloaded the servers
    mock_main_client.reload_servers.assert_called_once()


async def test_install_server_already_installed(
    hub_manager, mock_prompt_session, mock_config_manager
):
    """Test that installing an already installed server is handled gracefully."""
    # Arrange
    server_name = "test/existing-server"
    mock_prompt_session.prompt_async.side_effect = [server_name]
    mock_config_manager.get_installed_servers.return_value = [
        {"qualifiedName": server_name}
    ]

    # Act
    await hub_manager.install_server()

    # Assert
    # Check that a message was printed and we exited early
    hub_manager.console.print.assert_called_with(
        f"[yellow]Server '{server_name}' is already installed.[/yellow]"
    )
    # Ensure we did not try to add the server again
    mock_config_manager.add_installed_server.assert_not_called()


async def test_uninstall_server_happy_path(
    hub_manager, mock_prompt_session, mock_config_manager, mock_main_client
):
    """Test the successful uninstallation of a server."""
    # Arrange
    server_to_uninstall = {
        "qualifiedName": "test/to-uninstall",
        "displayName": "Uninstall Me",
    }
    mock_config_manager.get_installed_servers.return_value = [server_to_uninstall]
    mock_prompt_session.prompt_async.side_effect = [
        "1",
        "DELETE",
    ]  # User chooses the first server, confirms

    # Act
    await hub_manager.uninstall_server()

    # Assert
    # 1. Fetched the list of servers
    mock_config_manager.get_installed_servers.assert_called_once_with("default")
    # 2. Removed the correct server
    mock_config_manager.remove_installed_server.assert_called_once_with(
        "test/to-uninstall", "default"
    )
    # 3. Reloaded servers
    mock_main_client.reload_servers.assert_called_once()


async def test_toggle_server_status(
    hub_manager, mock_prompt_session, mock_config_manager, mock_main_client
):
    """Test toggling a server from enabled to disabled."""
    # Arrange
    server_to_toggle = {
        "qualifiedName": "test/toggle-me",
        "displayName": "Toggle Me",
        "enabled": True,
    }
    mock_config_manager.get_installed_servers.return_value = [server_to_toggle]
    # Simulate loading the config for modification
    mock_config_manager.load_configuration.return_value = {
        "installed_servers": [server_to_toggle]
    }
    mock_prompt_session.prompt_async.side_effect = ["1"]

    # Act
    await hub_manager.toggle_server_enabled_status()

    # Assert
    # 1. Saved the updated configuration
    mock_config_manager.save_configuration.assert_called_once()
    # 2. The saved data should have the server as disabled
    saved_config = mock_config_manager.save_configuration.call_args[0][0]
    assert saved_config["installed_servers"][0]["enabled"] is False
    # 3. Reloaded servers
    mock_main_client.reload_servers.assert_called_once()
