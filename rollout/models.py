import os
import logging
import tomllib
from openai import AzureOpenAI, OpenAI
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# Path to configuration file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "model_config.toml")

# Load configuration
def load_config():
    """Load model configuration from TOML file"""
    try:
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {CONFIG_PATH}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        raise

# Client cache
client_cache = {}

def get_client(model_name):
    """
    Get or create API client for the model
    
    Args:
        model_name: Model name
    
    Returns:
        Client object with configuration
    """
    # Return cached client if available
    if model_name in client_cache:
        return client_cache[model_name]
    
    # Load configuration
    config = load_config()
    
    # Check if model exists in configuration
    if model_name not in config["models"]:
        raise ValueError(f"Model '{model_name}' not defined in configuration file")
    
    model_config = config["models"][model_name]
    client_type = model_config["type"]
    
    # Create client based on type
    if client_type == "azure":
        client = AzureOpenAI(
            azure_endpoint=model_config["endpoint"],
            api_key=model_config["api_key"],
            api_version=model_config["api_version"],
        )
    elif client_type == "anthropic":
        client = Anthropic(
            api_key=model_config["api_key"],
        )
    elif client_type == "openai":
        client = OpenAI(
            base_url=model_config["base_url"] if "base_url" in model_config else None,
            api_key=model_config["api_key"],
        )
    else:
        raise ValueError(f"Unsupported client type: {client_type}")
    
    # Cache client for reuse
    client_cache[model_name] = {
        "client": client,
        "config": model_config
    }
    
    return client_cache[model_name]

def chat(messages, model="gpt-4o"):
    """
    Unified chat interface that automatically selects the correct client and calling method based on model name
    
    Args:
        messages: Message list
        model: Model name
        env_update_model: Model name for environment updates (if None, uses same model)
    
    Returns:
        Generated response content
    """
    try:
        client_data = get_client(model)
        client = client_data["client"]
        config = client_data["config"]
        
        logger.info(f"Using model: {model} (type: {config['type']})")
        
        if config["type"] == "azure":
            # Azure OpenAI API call
            params = {"model": config["model_name"], "messages": messages}
            
            # Add optional parameters (if specified in config)
            if "temperature" in config:
                params["temperature"] = config["temperature"]
            if "max_tokens" in config and config["model_name"] not in ["o1", "o1-preview", "o1-mini", "o3-mini"]:
                params["max_tokens"] = config["max_tokens"]
            
            completion = client.chat.completions.create(**params)
            return completion.choices[0].message.content
            
        elif config["type"] == "anthropic":
            # Anthropic API call
            params = {
                "model": config["model_name"],
                "messages": messages,
            }
            if "max_tokens" in config:
                params["max_tokens"] = config["max_tokens"]
                
            message = client.messages.create(**params)
            return message.content[0].text
            
        elif config["type"] == "openai":
            # Standard OpenAI compatible API call
            params = {
                "model": config["model_name"],
                "messages": messages,
            }
            
            # Add optional parameters
            if "temperature" in config:
                params["temperature"] = config["temperature"]
            if "max_tokens" in config:
                params["max_tokens"] = config["max_tokens"]
                
            completion = client.chat.completions.create(**params)
            return completion.choices[0].message.content
            
    except Exception as e:
        logger.error(f"Chat API call error: {str(e)}")
        return None

# Environment update specific interface
def update_environment(messages, model="gpt-4o"):
    """Environment update model call interface"""
    return chat(messages, model=model)

# Get all available models
def get_available_models():
    """Return list of all model names defined in configuration file"""
    config = load_config()
    return list(config["models"].keys())
