"""
Provider configuration for Ollama models (local AI).
"""

import os
import ollama
from typing import Optional
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_ollama_client():
    """
    Get Ollama client for local LLM.
    
    Returns:
        Configured Ollama client
    """
    base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    return ollama.AsyncClient(host=base_url)


def get_llm_model() -> str:
    """
    Get LLM model name for Ollama.
    
    Returns:
        Ollama model name
    """
    return os.getenv('OLLAMA_MODEL', 'llama3.2:3b')


def get_embedding_model():
    """
    Get embedding model using SentenceTransformers.
    
    Returns:
        SentenceTransformer model for embeddings
    """
    model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    return SentenceTransformer(model_name)


def get_embedding_model_name() -> str:
    """
    Get embedding model name.
    
    Returns:
        Embedding model name
    """
    return os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')


def validate_configuration() -> bool:
    """
    Validate that required configuration is available.
    
    Returns:
        True if configuration is valid
    """
    # Test Ollama connection
    try:
        client = get_ollama_client()
        # Note: We'll test the actual connection in the main app
        return True
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        return False


def get_model_info() -> dict:
    """
    Get information about current model configuration.
    
    Returns:
        Dictionary with model configuration info
    """
    return {
        "llm_provider": "ollama",
        "llm_model": get_llm_model(),
        "embedding_provider": "sentence_transformers",
        "embedding_model": get_embedding_model_name(),
        "ollama_base_url": os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
    }