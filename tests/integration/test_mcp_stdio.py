"""End to end check: start the real server over stdio and call both tools."""

import asyncio
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
KB = ROOT / "data" / "knowledge_base.json"


async def _session_calls():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.main"],
        cwd=str(ROOT),
        env={
            **{k: v for k, v in os.environ.items() if k != "LITELLM_KEY"},
            "RAG_KB_PATH": str(KB),
            "RAG_LITELLM_ENABLED": "false",
        },
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name for t in (await session.list_tools()).tools}
            hit = await session.call_tool("rag-search", {"query": "how do I undo a pushed commit"})
            miss = await session.call_tool("rag-generate", {"query": "how do I undo a pushed commit"})
            return tools, hit, miss


@pytest.mark.skipif(not KB.exists(), reason="run `make kb` first")
def test_mcp_roundtrip():
    tools, hit, miss = asyncio.run(_session_calls())
    assert tools == {"rag-search", "rag-generate"}
    assert not hit.isError and "revert" in hit.content[0].text
    assert miss.isError  # generation is disabled without LITELLM_KEY
