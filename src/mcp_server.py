"""
MCP server for the RAG service.

Exposes two tools over stdio so any MCP client (Copilot CLI, Claude Desktop,
VS Code) can call them:

    rag-search    fast semantic search, no LLM involved
    rag-generate  search plus an LLM written answer, needs LITELLM_KEY
"""

import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .core import KnowledgeBase, Retriever, Generator, SearchResult

logger = logging.getLogger(__name__)

MIN_QUERY_LENGTH = 3
MAX_TOP_K = 10
SNIPPET_CHARS = 500


class RAGMCPServer:
    """Registers the RAG tools on a FastMCP server."""

    def __init__(
        self,
        kb: KnowledgeBase,
        retriever: Retriever,
        generator: Optional[Generator] = None,
        name: str = "rag-mcp",
        host: str = "127.0.0.1",
        port: int = 18743,
    ):
        self.kb = kb
        self.retriever = retriever
        self.generator = generator
        self.mcp = FastMCP(name, host=host, port=port)
        self._register_tools()

    @staticmethod
    def _validate(query: str, top_k: int) -> None:
        if not query or len(query.strip()) < MIN_QUERY_LENGTH:
            raise ValueError(f"query must be at least {MIN_QUERY_LENGTH} characters")
        if not 1 <= top_k <= MAX_TOP_K:
            raise ValueError(f"top_k must be between 1 and {MAX_TOP_K}")

    @staticmethod
    def _format_results(results: list[SearchResult]) -> str:
        if not results:
            return "No results found."
        return "\n\n".join(
            f"[{i}] relevance {r.relevance:.0%}\n{r.text[:SNIPPET_CHARS]}"
            for i, r in enumerate(results, 1)
        )

    def search(self, query: str, top_k: int = 3) -> str:
        self._validate(query, top_k)
        results = self.retriever.search(query, top_k=top_k)
        logger.info("search %r -> %d results", query, len(results))
        return self._format_results(results)

    def generate(self, query: str, top_k: int = 3) -> str:
        if self.generator is None:
            raise ValueError("generation is disabled, set LITELLM_KEY to enable it")
        self._validate(query, top_k)
        results = self.retriever.search(query, top_k=top_k)
        if not results:
            return "No relevant context found in the knowledge base."
        answer = self.generator.generate(query, results)
        sources = "\n".join(
            f"[{i}] ({r.relevance:.0%}) {r.text[:80]}..." for i, r in enumerate(results, 1)
        )
        logger.info("generate %r from %d chunks", query, len(results))
        return f"{answer}\n\nSources\n{sources}"

    def _register_tools(self) -> None:
        @self.mcp.custom_route("/health", methods=["GET"])
        async def health(_request):
            from starlette.responses import JSONResponse
            return JSONResponse({"status": "ok", "chunks": len(self.kb)})

        self.mcp.tool(
            name="rag-search",
            description=(
                "Semantic search over the knowledge base. Returns the most relevant "
                "chunks with relevance scores. Fast and free, no LLM call."
            ),
        )(self.search)
        self.mcp.tool(
            name="rag-generate",
            description=(
                "Search the knowledge base and write an answer from the best chunks "
                "using an LLM. Needs LITELLM_KEY."
            ),
        )(self.generate)

    def run(self, transport: str = "stdio") -> None:
        """Serve until the client disconnects (stdio) or the process stops (http)."""
        logger.info("MCP server ready (%d chunks, transport=%s)", len(self.kb), transport)
        if transport == "http":
            self.mcp.run(transport="streamable-http")
        else:
            self.mcp.run(transport="stdio")
