"""
RAG Service - Core Business Logic

This module contains the domain logic for retrieval augmented generation.
No infrastructure concerns, no MCP, no HTTP - pure business logic.

Usage:
    from src.core import KnowledgeBase, Retriever, Generator
    
    kb = KnowledgeBase.load("data/knowledge_base.json")
    retriever = Retriever(kb)
    results = retriever.search("what is caching?", top_k=3)
"""

import json
import logging
from pathlib import Path
from typing import NamedTuple
from dataclasses import dataclass

import numpy as np


logger = logging.getLogger(__name__)


class SearchResult(NamedTuple):
    """Single search result with metadata."""
    text: str
    relevance: float
    chunk_id: int


@dataclass
class KnowledgeBase:
    """In-memory knowledge base with embeddings."""
    
    chunks: list  # [{text, embedding, id}, ...]
    metadata: dict  # Version, created_at, chunk_count
    
    @classmethod
    def load(cls, path: Path) -> "KnowledgeBase":
        """
        Load knowledge base from JSON file.
        
        Args:
            path: Path to knowledge_base.json
        
        Returns:
            KnowledgeBase instance
        
        Raises:
            FileNotFoundError: If file not found
            ValueError: If file format invalid
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"KB file not found: {path}")
        
        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in KB file: {e}")
        
        if not isinstance(data, dict) or "chunks" not in data:
            raise ValueError("KB file must contain 'chunks' key")
        
        chunks = data["chunks"]
        if not chunks:
            logger.warning("Knowledge base is empty")
        
        logger.info(f"Loaded KB with {len(chunks)} chunks")
        
        return cls(
            chunks=chunks,
            metadata=data.get("metadata", {})
        )
    
    def __len__(self) -> int:
        return len(self.chunks)


class Retriever:
    """Semantic search using cosine similarity."""
    
    def __init__(self, kb: KnowledgeBase):
        """
        Initialize retriever with knowledge base.
        
        Args:
            kb: KnowledgeBase instance
        """
        self.kb = kb
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        mag1 = np.linalg.norm(vec1)
        mag2 = np.linalg.norm(vec2)
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return float(dot_product / (mag1 * mag2))
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a search query using fastembed.
        
        This is called per-query, so embeddings are fresh.
        The model is cached after first download.
        
        Args:
            query: Natural language question
        
        Returns:
            384-dimensional embedding vector
        
        Raises:
            ImportError: If fastembed not installed
        """
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise ImportError(
                "fastembed not installed. Run: pip install fastembed"
            )
        
        model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        embedding = list(model.embed([query]))[0]
        return np.array(embedding)
    
    def search(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.0
    ) -> list[SearchResult]:
        """
        Search knowledge base for relevant chunks.
        
        Args:
            query: Natural language question
            top_k: Number of results to return
            min_similarity: Minimum relevance score (0.0 to 1.0)
        
        Returns:
            List of SearchResult objects, sorted by relevance (highest first)
        
        Raises:
            ValueError: If KB empty or invalid parameters
        """
        if not self.kb.chunks:
            raise ValueError("Knowledge base is empty")
        
        if not 0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between 0.0 and 1.0")
        
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        
        # Embed query
        query_vec = self.embed_query(query)
        
        # Compute similarity to all chunks
        similarities = []
        for chunk_id, chunk in enumerate(self.kb.chunks):
            chunk_vec = np.array(chunk["embedding"])
            sim = self._cosine_similarity(query_vec, chunk_vec)
            
            if sim >= min_similarity:
                similarities.append(
                    SearchResult(
                        text=chunk["text"],
                        relevance=sim,
                        chunk_id=chunk_id
                    )
                )
        
        # Sort by relevance descending
        similarities.sort(key=lambda x: x.relevance, reverse=True)
        
        self.logger.info(
            f"Query '{query[:50]}...' found {len(similarities)} results, "
            f"returning top {min(len(similarities), top_k)}"
        )
        
        return similarities[:top_k]


class Generator:
    """Generate answers using LLM with retrieved context."""
    
    def __init__(self, litellm_key: str, litellm_url: str, model: str):
        """
        Initialize LLM-based generator.
        
        Args:
            litellm_key: API key for LiteLLM proxy
            litellm_url: Base URL of LiteLLM proxy
            model: Model name on proxy (e.g., "claude-sonnet-5")
        
        Raises:
            ValueError: If credentials invalid
        """
        if not litellm_key:
            raise ValueError("litellm_key required")
        
        self.litellm_key = litellm_key
        self.litellm_url = litellm_url
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    def generate(
        self,
        query: str,
        context_results: list[SearchResult],
        max_tokens: int = 500
    ) -> str:
        """
        Generate an answer using retrieved context.
        
        Args:
            query: Original question
            context_results: List of SearchResult from Retriever
            max_tokens: Max response length
        
        Returns:
            Generated answer text
        
        Raises:
            ImportError: If litellm not installed
            RuntimeError: If API call fails
        """
        try:
            from litellm import completion
        except ImportError:
            raise ImportError("litellm not installed. Run: pip install litellm")
        
        if not context_results:
            return "No relevant context found in knowledge base."
        
        # Build context string
        context_text = "\n\n".join([
            f"[Relevance: {r.relevance:.1%}]\n{r.text}"
            for r in context_results
        ])
        
        prompt = f"""You are a knowledge base assistant. Answer the question using ONLY the provided context.
If the context doesn't contain the answer, say so clearly.

Context:
{context_text}

Question: {query}

Answer:"""
        
        try:
            response = completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.litellm_key,
                api_base=self.litellm_url,
                max_tokens=max_tokens,
                temperature=0.2
            )
            
            answer = response.choices[0].message.content
            
            self.logger.info(
                f"Generated answer for '{query[:50]}...' "
                f"({len(answer)} chars, {len(context_results)} context chunks)"
            )
            
            return answer
            
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            raise RuntimeError(f"Failed to generate answer: {e}")
