"""
Unit tests for core RAG components.

Run with: pytest tests/unit/
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import json

from src.core import KnowledgeBase, Retriever, SearchResult


@pytest.fixture
def sample_kb():
    """Create a sample knowledge base for testing."""
    chunks = [
        {
            "text": "Caching improves performance by storing computed results.",
            "embedding": [0.1] * 384
        },
        {
            "text": "Database transactions ensure ACID properties.",
            "embedding": [0.2] * 384
        },
        {
            "text": "API authentication uses JWT tokens.",
            "embedding": [0.3] * 384
        }
    ]
    return KnowledgeBase(chunks=chunks, metadata={"version": "1.0"})


class TestKnowledgeBase:
    """Test KnowledgeBase loading and structure."""
    
    def test_load_valid_kb(self, sample_kb):
        """Test loading a valid KB."""
        assert len(sample_kb) == 3
        assert sample_kb.metadata["version"] == "1.0"
    
    def test_load_missing_kb(self):
        """Test error handling for missing KB file."""
        with pytest.raises(FileNotFoundError):
            KnowledgeBase.load(Path("nonexistent.json"))
    
    def test_load_invalid_json(self):
        """Test error handling for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {")
            f.flush()
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError):
                KnowledgeBase.load(temp_path)
        finally:
            temp_path.unlink()
    
    def test_load_missing_chunks_key(self):
        """Test error handling when 'chunks' key missing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"metadata": {}}, f)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError):
                KnowledgeBase.load(temp_path)
        finally:
            temp_path.unlink()


class TestRetriever:
    """Test search and retrieval logic."""
    
    def test_cosine_similarity(self, sample_kb):
        """Test cosine similarity calculation."""
        retriever = Retriever(sample_kb)
        
        # Identical vectors should have similarity 1.0
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        assert retriever._cosine_similarity(vec1, vec2) == pytest.approx(1.0)
        
        # Orthogonal vectors should have similarity 0.0
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        assert retriever._cosine_similarity(vec1, vec2) == pytest.approx(0.0)
        
        # Zero vectors should have similarity 0.0
        vec1 = np.array([0.0, 0.0, 0.0])
        vec2 = np.array([1.0, 1.0, 1.0])
        assert retriever._cosine_similarity(vec1, vec2) == pytest.approx(0.0)
    
    def test_search_empty_kb(self):
        """Test search on empty KB."""
        empty_kb = KnowledgeBase(chunks=[], metadata={})
        retriever = Retriever(empty_kb)
        
        with pytest.raises(ValueError, match="empty"):
            retriever.search("test query")
    
    def test_search_invalid_parameters(self, sample_kb):
        """Test search parameter validation."""
        retriever = Retriever(sample_kb)
        
        # Invalid top_k
        with pytest.raises(ValueError):
            retriever.search("test", top_k=0)
        
        with pytest.raises(ValueError):
            retriever.search("test", top_k=-1)
        
        # Invalid similarity threshold
        with pytest.raises(ValueError):
            retriever.search("test", min_similarity=1.5)
        
        with pytest.raises(ValueError):
            retriever.search("test", min_similarity=-0.1)
    
    def test_search_returns_top_k(self, sample_kb):
        """Test that search returns at most top_k results."""
        retriever = Retriever(sample_kb)
        
        # Mock the embed_query to avoid fastembed dependency in tests
        def mock_embed(query):
            return np.array([0.1] * 384)
        
        retriever.embed_query = mock_embed
        
        results = retriever.search("test query", top_k=2)
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)
    
    def test_search_results_sorted_by_relevance(self, sample_kb):
        """Test that results are sorted by relevance."""
        retriever = Retriever(sample_kb)
        
        def mock_embed(query):
            return np.array([0.1] * 384)
        
        retriever.embed_query = mock_embed
        results = retriever.search("test query", top_k=10)
        
        # Results should be sorted descending
        relevances = [r.relevance for r in results]
        assert relevances == sorted(relevances, reverse=True)


class TestSearchResult:
    """Test SearchResult data structure."""
    
    def test_search_result_fields(self):
        """Test SearchResult has required fields."""
        result = SearchResult(
            text="Test chunk",
            relevance=0.85,
            chunk_id=0
        )
        
        assert result.text == "Test chunk"
        assert result.relevance == 0.85
        assert result.chunk_id == 0
    
    def test_search_result_immutable(self):
        """Test that SearchResult is immutable (NamedTuple)."""
        result = SearchResult(text="Test", relevance=0.5, chunk_id=0)
        
        with pytest.raises(AttributeError):
            result.text = "Changed"
