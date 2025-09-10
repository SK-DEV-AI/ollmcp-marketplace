"""Default configuration settings for MCP Client for Ollama.

This module provides default settings and paths used throughout the application.
These defaults ensure the application starts with sensible values for model selection,
tool enabling, context retention, and Ollama model options.
"""

import os
from ..utils.constants import DEFAULT_MODEL, DEFAULT_CONFIG_FILE, DEFAULT_CONFIG_DIR


def default_config() -> dict:
    """Get default configuration settings.

    This function returns a comprehensive default configuration dictionary
    that includes:
    - Model selection (default Ollama model)
    - Tool management (initially empty, populated at runtime)
    - Context retention settings for conversation history
    - Model-specific settings for thinking mode and display
    - Detailed Ollama model configuration parameters (system prompt, sampling options, etc.)
    - Display preferences for tool execution and metrics
    - Human-in-the-loop confirmation settings

    Returns:
        dict: Default configuration dictionary with all initial settings.
    """

    return {
        "model": DEFAULT_MODEL,  # Default Ollama model to use for inference
        "enabledTools": {},  # Dictionary of tool names mapped to boolean enabled status; populated with available tools at runtime
        "contextSettings": {"retainContext": True},  # Whether to maintain conversation history across queries
        "modelSettings": {
            "thinkingMode": True,  # Enable step-by-step reasoning mode if supported by the model
            "showThinking": False,  # Whether to display the thinking process in the final response
        },
        "modelConfig": {
            "system_prompt": "",  # Custom system prompt to guide model behavior
            "num_keep": None,  # Number of tokens to keep from the previous context (for context window management)
            "seed": None,  # Random seed for reproducible generations (None for random)
            "num_predict": None,  # Maximum number of tokens to predict/generate
            "top_k": None,  # Top-K sampling parameter (limits sampling to top K tokens)
            "top_p": None,  # Top-P (nucleus) sampling parameter (cumulative probability threshold)
            "min_p": None,  # Minimum probability for token sampling (Mirostat-like)
            "typical_p": None,  # Typical sampling parameter for more focused outputs
            "repeat_last_n": None,  # Number of last tokens to consider for repetition penalty
            "temperature": None,  # Sampling temperature (higher = more random, lower = more deterministic)
            "repeat_penalty": None,  # Penalty for repeating tokens to encourage diversity
            "presence_penalty": None,  # Penalty for tokens already present in the text
            "frequency_penalty": None,  # Penalty based on token frequency to reduce repetition
            "stop": None,  # List of stop tokens/phrases to halt generation
            "num_ctx": None,  # Context window size (maximum tokens for input)
        },
        "displaySettings": {
            "showToolExecution": True,  # Display detailed tool execution logs and results
            "showMetrics": False,  # Show performance metrics (tokens, time) after each query
        },
        "hilSettings": {"enabled": True},  # Enable human-in-the-loop confirmations for tool calls
    }


def get_config_path(config_name: str = "default") -> str:
    """Get the path to a specific configuration file.

    This utility ensures the configuration directory exists and sanitizes the config name
    to prevent filesystem issues. Supports named configurations beyond the default.

    Args:
        config_name: Name of the configuration (default: "default"). Sanitized to alphanumeric, hyphens, underscores.

    Returns:
        str: Full path to the configuration file in the default config directory.
    """
    # Ensure the directory exists
    os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)

    # Sanitize the config name
    config_name = (
        "".join(c for c in config_name if c.isalnum() or c in ["-", "_"]).lower()
        or "default"
    )

    if config_name == "default":
        return os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE)
    else:
        return os.path.join(DEFAULT_CONFIG_DIR, f"{config_name}.json")
