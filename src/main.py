"""
Main entry point for RAG MCP service.

Initializes configuration, logging, components, and starts the MCP server.
"""

import os
import sys
import logging
from pathlib import Path

from src.config import load_config, setup_logging
from src.core import KnowledgeBase, Retriever, Generator
from src.mcp_server import RAGMCPServer


def main():
    """Start the RAG MCP service."""
    
    try:
        # Load configuration
        config = load_config()
        
        # Setup logging
        setup_logging(config)
        logger = logging.getLogger(__name__)
        
        logger.info(f"Starting {config.service_name} v{config.version}")
        logger.info(f"Environment: {config.environment}")
        logger.info(f"KB: {config.kb_path.name} ({config.kb_path.parent.name}/)")
        
        # Load knowledge base
        logger.info("Loading knowledge base...")
        kb = KnowledgeBase.load(config.kb_path)
        logger.info(f"Loaded {len(kb)} chunks")
        
        # Initialize retriever
        retriever = Retriever(kb)
        
        # Initialize generator (if enabled)
        generator = None
        if config.litellm_enabled and config.litellm_key:
            logger.info("Initializing LLM generator...")
            generator = Generator(
                litellm_key=config.litellm_key,
                litellm_url=config.litellm_base_url,
                model=config.litellm_model
            )
            logger.info(f"LLM: {config.litellm_model}")
        else:
            logger.info("LLM generation disabled")
        
        # Start MCP server
        logger.info("Starting MCP server...")
        transport = os.getenv("RAG_TRANSPORT", "stdio").lower()
        mcp_server = RAGMCPServer(
            kb,
            retriever,
            generator,
            host=os.getenv("RAG_HOST", "127.0.0.1"),
            port=int(os.getenv("RAG_PORT", "18743")),
        )
        mcp_server.run(transport=transport)
        
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"CONFIG ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
