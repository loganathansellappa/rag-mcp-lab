"""
Configuration management for RAG service.

Loads from config files (YAML/JSON) with environment variable overrides.
Validates all settings at startup.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Production service configuration with validation."""
    
    # Service
    service_name: str = "rag-mcp"
    version: str = "1.0.0"
    environment: str = "development"  # development, staging, production
    
    # Paths
    kb_path: Path = field(default_factory=lambda: Path("data/knowledge_base.json"))
    config_dir: Path = field(default_factory=lambda: Path("config"))
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    
    # LiteLLM (for generation)
    litellm_enabled: bool = True
    litellm_key: Optional[str] = None
    litellm_base_url: str = "https://litellm.platform.tvcorp.tvplatform2.org"
    litellm_model: str = "claude-sonnet-5"
    litellm_timeout: int = 30
    
    # Search parameters
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    default_top_k: int = 3
    min_similarity_threshold: float = 0.3
    
    # Server
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    request_timeout: int = 60
    max_concurrent: int = 10
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def validate(self) -> None:
        """
        Validate configuration at startup.
        
        Raises:
            ValueError: If any required settings invalid
            FileNotFoundError: If required files missing
        """
        # Check KB path
        if not self.kb_path.exists():
            raise FileNotFoundError(
                f"Knowledge base not found: {self.kb_path}\n"
                f"Run `make kb` first or set RAG_KB_PATH"
            )
        
        # Check litellm if enabled
        if self.litellm_enabled and not self.litellm_key:
            logger.warning("LITELLM_KEY not set, rag-generate disabled, rag-search still works")
            self.litellm_enabled = False
        
        # Validate numeric ranges
        if not (0 <= self.min_similarity_threshold <= 1.0):
            raise ValueError(f"min_similarity_threshold must be 0.0-1.0")
        
        if self.default_top_k < 1:
            raise ValueError(f"default_top_k must be >= 1")
        
        if self.litellm_timeout < 1:
            raise ValueError(f"litellm_timeout must be >= 1")
        
        # Validate log level
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if self.log_level not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        
        logger.info(f"Config validated: {self.environment} environment, "
                   f"KB={self.kb_path.name}, LiteLLM={'enabled' if self.litellm_enabled else 'disabled'}")
    
    def to_dict(self) -> dict:
        """Export config as dictionary (excluding secrets)."""
        return {
            "service_name": self.service_name,
            "version": self.version,
            "environment": self.environment,
            "kb_path": str(self.kb_path),
            "litellm_enabled": self.litellm_enabled,
            "litellm_model": self.litellm_model,
            "default_top_k": self.default_top_k,
            "embedding_model": self.embedding_model,
        }


def load_config(
    config_file: Optional[str] = None,
    service_root: Optional[Path] = None
) -> ServiceConfig:
    """
    Load configuration from file and environment variables.
    
    Precedence (highest to lowest):
    1. Environment variables (RAG_*)
    2. Config file (YAML or JSON)
    3. Defaults
    
    Args:
        config_file: Path to config.yaml/config.json (optional)
        service_root: Root directory for relative paths (defaults to script dir)
    
    Returns:
        Validated ServiceConfig instance
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config invalid
    """
    
    if service_root is None:
        service_root = Path(__file__).parent.parent
    
    config = ServiceConfig()
    
    # Convert paths to be relative to service root
    config.kb_path = service_root / "data" / "knowledge_base.json"
    config.config_dir = service_root / "config"
    config.log_dir = service_root / "logs"
    
    # Load from config file if provided
    if config_file:
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        logger.info(f"Loading config from {config_file}")
        
        if config_file.endswith(".json"):
            with open(config_path) as f:
                data = json.load(f)
        else:
            try:
                import yaml
                with open(config_path) as f:
                    data = yaml.safe_load(f)
            except ImportError:
                raise ImportError(
                    "YAML config requires pyyaml. Run: pip install pyyaml"
                )
        
        # Update from file (only known fields)
        allowed_fields = {
            "service_name", "version", "environment",
            "litellm_enabled", "litellm_model", "litellm_base_url",
            "litellm_timeout", "default_top_k", "min_similarity_threshold",
            "embedding_model", "log_level", "server_host", "server_port",
            "request_timeout", "max_concurrent"
        }
        
        for key, value in data.items():
            if key in allowed_fields:
                setattr(config, key, value)
    
    # Override with environment variables (highest precedence)
    if kb_path := os.getenv("RAG_KB_PATH"):
        config.kb_path = Path(kb_path)
    
    if litellm_key := os.getenv("LITELLM_KEY"):
        config.litellm_key = litellm_key
    
    if litellm_enabled := os.getenv("RAG_LITELLM_ENABLED"):
        config.litellm_enabled = litellm_enabled.lower() in ("1", "true", "yes")
    
    if log_level := os.getenv("RAG_LOG_LEVEL"):
        config.log_level = log_level
    
    if environment := os.getenv("RAG_ENVIRONMENT"):
        config.environment = environment
    
    if top_k := os.getenv("RAG_DEFAULT_TOP_K"):
        try:
            config.default_top_k = int(top_k)
        except ValueError:
            raise ValueError(f"RAG_DEFAULT_TOP_K must be integer, got: {top_k}")
    
    # Create required directories
    config.log_dir.mkdir(parents=True, exist_ok=True)
    config.config_dir.mkdir(parents=True, exist_ok=True)
    
    # Validate everything
    config.validate()
    
    return config


def setup_logging(config: ServiceConfig) -> logging.Logger:
    """
    Configure logging with file and console handlers.
    
    Args:
        config: ServiceConfig instance
    
    Returns:
        Configured root logger
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.log_level))
    
    # Formatter
    formatter = logging.Formatter(config.log_format)
    
    # Console handler (stderr)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_file = config.log_dir / f"{config.service_name}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_log_file = config.log_dir / f"{config.service_name}-error.log"
    error_handler = logging.FileHandler(error_log_file)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    logger.info(f"Logging configured: {config.log_level} to {log_file}")
    
    return logger
