<p align="center">
  <a href="https://github.com/SK-DEV-AI/ollmcp-marketplace">
    <img src="https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-logo-512.png?raw=true" width="256" />
  </a>
</p>
<p align="center">
  <h1>MCP Client for Ollama & Marketplace</h1>
</p>
<p align="center">
<i>A simple yet powerful Python client for interacting with MCP servers using Ollama, now featuring the <b>MCP-HUB</b> for discovering and managing tools from the Smithery.ai registry.</i>
</p>

---

# MCP Client for Ollama (ollmcp)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI - Python Version](https://img.shields.io/pypi/v/mcp-client-for-ollama?label=mcp-client-for-ollama-pypi)](https://pypi.org/project/mcp-client-for-ollama/)
[![Build, Publish and Release](https://github.com/SK-DEV-AI/ollmcp-marketplace/actions/workflows/publish.yml/badge.svg)](https://github.com/SK-DEV-AI/ollmcp-marketplace/actions/workflows/publish.yml)
[![CI](https://github.com/SK-DEV-AI/ollmcp-marketplace/actions/workflows/ci.yml/badge.svg)](https://github.com/SK-DEV-AI/ollmcp-marketplace/actions/workflows/ci.yml)

<p align="center">
  <img src="https://raw.githubusercontent.com/jonigl/mcp-client-for-ollama/v0.15.0/misc/ollmcp-demo.gif" alt="MCP Client for Ollama Demo">
</p>
<p align="center">
  <a href="https://asciinema.org/a/jxc6N8oKZAWrzH8aK867zhXdO" target="_blank">🎥 Watch the original demo as an Asciinema recording</a>
</p>

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [The MCP-HUB Marketplace](#the-mcp-hub-marketplace)
  - [Hub Overview](#hub-overview)
  - [Hub Commands](#hub-commands)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Command-line Arguments](#command-line-arguments)
  - [Usage Examples](#usage-examples)
- [Interactive Commands](#interactive-commands)
- [Configuration Management](#configuration-management)
- [Compatible Models](#compatible-models)
- [Where Can I Find More MCP Servers?](#where-can-i-find-more-mcp-servers)
- [Related Projects](#related-projects)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Overview

MCP Client for Ollama (`ollmcp`) is a modern, interactive terminal application (TUI) for connecting local Ollama LLMs to one or more Model Context Protocol (MCP) servers, enabling advanced tool use and workflow automation.

This enhanced version includes the **MCP-HUB**, a powerful, integrated marketplace for discovering, installing, and managing MCP servers from the [Smithery.ai](https://smithery.ai/) registry. With a rich, user-friendly interface, it lets you manage tools, models, and server connections in real time—no coding required.

## Features

- 📦 **MCP-HUB Marketplace**: An integrated hub to discover, install, manage, and configure MCP servers from the Smithery.ai registry.
- 🌐 **Multi-Server Support**: Connect to multiple MCP servers simultaneously.
- 🚀 **Multiple Transport Types**: Supports STDIO, SSE, and Streamable HTTP server connections.
- 🛠️ **Full Tool Lifecycle Management**: Enable/disable, re-configure, and view installed servers on the fly.
- 🧠 **Advanced Model Configuration**: Fine-tune 15+ model parameters and customize system prompts.
- 🧑‍💻 **Human-in-the-Loop (HIL)**: Review and approve tool executions before they run for enhanced control and safety.
- 🤔 **Thinking Mode**: Advanced reasoning capabilities with visible thought processes for supported models.
- 💾 **Named Configurations**: Save and load multiple configurations for different tasks and workflows. The MCP-HUB is fully integrated with this system.
- 🔄 **Live Server Reloading**: Hot-reload MCP servers after any change (install, uninstall, enable/disable) without restarting the client.
- ✨ **Fuzzy Autocomplete** & **Dynamic Prompt**: A modern TUI with interactive command completion and a contextual prompt.
- 📊 **Performance Metrics**: Detailed model performance data after each query.
- 🔔 **Update Notifications**: Automatically detects when a new version is available.

## The MCP-HUB Marketplace

The MCP-HUB is your central command center for managing MCP servers. It transforms `ollmcp` from a simple client into a full-fledged development and exploration tool for local LLM tool use.

### Hub Overview

To enter the hub, simply type `hub` or `mcphub` in the main chat prompt. You will be greeted with a menu of options to manage your servers. The hub is fully integrated with `ollmcp`'s named configuration system, meaning any servers you install or manage will be correctly associated with your currently active configuration profile.

### Hub Commands

| Command                        | Description                                                                          |
| ------------------------------ | ------------------------------------------------------------------------------------ |
| `Search for servers`           | Search the Smithery.ai registry for new MCP servers. Supports advanced filters.      |
| `Install a server`             | Install a new server from the registry. Guides you through configuration.            |
| `Uninstall a server`           | Remove an installed server. The change is applied immediately.                       |
| `View installed servers`       | See detailed information and the saved configuration for all your installed servers. |
| `Enable/Disable a server`      | Temporarily enable or disable an installed server without uninstalling it.           |
| `Re-configure installed server`| Update the configuration of an already installed server.                             |
| `Inspect server from registry` | View the full details of any server on the registry before you decide to install.    |
| `Configure Smithery API Key`   | Set or update your Smithery.ai API key. A key is required to use the hub.          |
| `Clear API Cache`              | Manually clear the local cache of server details to fetch fresh data.                |
| `Back to main menu`            | Exit the hub and return to the main chat interface.                                  |

## Requirements

- **Python 3.10+** ([Installation guide](https://www.python.org/downloads/))
- **Ollama** running locally ([Installation guide](https://ollama.com/download))
- **UV package manager** (recommended) ([Installation guide](https://github.com/astral-sh/uv))

## Quick Start

**Option 1:** Install with pip and run

```bash
pip install --upgrade mcp-client-for-ollama
ollmcp
```

**Option 2:** One-step install and run with `uvx`

```bash
uvx mcp-client-for-ollama
```

**Option 3:** Install from source

```bash
git clone https://github.com/SK-DEV-AI/ollmcp-marketplace.git
cd ollmcp-marketplace
uv venv && source .venv/bin/activate
uv pip install .
ollmcp
```

**Option 4 (Arch Linux):** Build and install using the PKGBUILD

```bash
git clone https://github.com/SK-DEV-AI/ollmcp-marketplace.git
cd ollmcp-marketplace
makepkg -si
```

## Usage

Run with default settings, which will automatically discover servers from Claude's configuration if available:

```bash
ollmcp
```

### Command-line Arguments

The CLI uses `Typer` for a modern experience with grouped options and shell autocompletion. To install autocompletion, run `ollmcp --install-completion` and restart your shell.

- **MCP Server Configuration**: Use `--mcp-server` (`-s`) for local scripts, `--mcp-server-url` (`-u`) for remote URLs, or `--servers-json` (`-j`) for a config file. Use `--auto-discovery` (`-a`) to find Claude's servers.
- **Ollama Configuration**: Use `--model` (`-m`) to specify the model and `--host` (`-H`) for the Ollama URL.
- **General Options**: `--version` (`-v`) and `--help` (`-h`).

### Usage Examples

Connect to a single local server:
```bash
ollmcp -s /path/to/weather.py -m llama3.1
```

Connect to a remote server and use a named configuration:
```bash
ollmcp -u http://localhost:8000/mcp -m qwen3 && lc my-config
```

## Interactive Commands

During chat, type `help` or `h` to see a full list of commands. Key commands include:

| Command          | Shortcut         | Description                                                              |
|------------------|------------------|--------------------------------------------------------------------------|
| `hub`            | `mcphub`         | **Enter the MCP-HUB Marketplace to manage servers.**                     |
| `tools`          | `t`              | Open the tool selection interface for locally configured servers.        |
| `model`          | `m`              | List and select a different Ollama model.                                |
| `model-config`   | `mc`             | Configure advanced model parameters and the system prompt.               |
| `context`        | `c`              | Toggle conversation context retention.                                   |
| `human-in-loop`  | `hil`            | Toggle safety confirmations before tool execution.                       |
| `save-config`    | `sc`             | Save the current session (model, tools, etc.) to a named configuration.  |
| `load-config`    | `lc`             | Load a previously saved configuration.                                   |
| `reload-servers` | `rs`             | Reload all connected MCP servers.                                        |
| `quit`           | `q` or `Ctrl+D`  | Exit the client.                                                         |

## Configuration Management

The client supports saving and loading multiple named configurations. The MCP-HUB is fully integrated with this system. If you load a configuration named `my-api-tools`, any servers you install via the hub will be saved to that profile.

- Configurations are stored in `~/.config/ollmcp/`.
- The default configuration is `~/.config/ollmcp/config.json`.
- Named configurations are saved as `~/.config/ollmcp/{name}.json`.

## Compatible Models

Most modern Ollama models with function calling/tool use capabilities are compatible. Recommended models include:

- `qwen2.5`, `qwen3`
- `llama3.1`, `llama3.2`
- `mistral-large`, `mistral-next`
- `gpt-oss`, `deepseek-r1`

For a complete list, visit the [official Ollama models page](https://ollama.com/search?c=tools).

## Where Can I Find More MCP Servers?

The primary way to discover and manage servers is through the built-in **MCP-HUB**, which connects to the [Smithery.ai](https://smithery.ai/search) registry.

You can also explore the official [MCP Servers repository](https://github.com/modelcontextprotocol/servers) for reference implementations.

## Related Projects

- **[Ollama MCP Bridge](https://github.com/jonigl/ollama-mcp-bridge)** - A Python API layer that sits in front of Ollama, automatically adding tools from multiple MCP servers to every chat request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Ollama](https://ollama.com/) for the local LLM runtime
- [Model Context Protocol](https://modelcontextprotocol.io/) for the specification and examples
- [Smithery.ai](https://smithery.ai/) for the MCP server registry and API
- [Rich](https://rich.readthedocs.io/) for the terminal user interface
- [Typer](https://typer.tiangolo.com/) for the modern CLI experience
- [Prompt Toolkit](https://python-prompt-toolkit.readthedocs.io/) for the interactive command line interface
- [UV](https://github.com/astral-sh/uv) for the lightning-fast Python package manager
- [Asciinema](https://asciinema.org/) for the demo recording

---

<p align="center">
Forked from <a href="https://github.com/jonigl/mcp-client-for-ollama">jonigl/mcp-client-for-ollama</a> and enhanced with the MCP-HUB Marketplace.
</p>
