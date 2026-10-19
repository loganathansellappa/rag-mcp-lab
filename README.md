# rag-mcp-lab

A small, production shaped RAG service that speaks MCP. Ask a question, get the most relevant chunks of your documents back, or a written answer with sources. Good for learning how embeddings, vector search and MCP fit together.

## Try it

```bash
git clone https://github.com/loganathansellappa/rag-mcp-lab.git
cd rag-mcp-lab
pip install -r requirements.txt
python -m src.main
```

A sample knowledge base is already built (`data/knowledge_base.json`, from three short docs in `data/docs/`), so the server starts right away. By default it talks MCP over stdio, so point a client at it. See [`examples/mcp-client.json`](examples/mcp-client.json).

## Run with Docker in the background

Build the image once:

```bash
docker build -f deployment/docker/Dockerfile -t rag-mcp:1.0.0 .
```

Start it detached, serving MCP over HTTP on port 18743 (an unusual port, so it won't clash with common services). It is bound to localhost only:

```bash
docker run -d --name rag-mcp \
  -p 127.0.0.1:18743:18743 \
  -e RAG_TRANSPORT=http -e RAG_HOST=0.0.0.0 \
  rag-mcp:1.0.0
```

Check it and point your MCP client at the URL:

```bash
curl http://127.0.0.1:18743/health      # {"status":"ok","chunks":18}
docker logs -f rag-mcp
docker stop rag-mcp && docker rm rag-mcp
```

MCP endpoint: `http://127.0.0.1:18743/mcp`, client config in [`examples/mcp-client-http.json`](examples/mcp-client-http.json). Add `-e LITELLM_KEY` to the `docker run` for `rag-generate`. To use your own KB, mount it, for example `-v ./data:/app/data:ro`.

Without `RAG_TRANSPORT=http` the container uses stdio and needs `docker run -i` instead of `-d`.

## Tools

| Tool | What it does | Needs |
|---|---|---|
| `rag-search` | Semantic search, returns chunks with relevance scores | nothing |
| `rag-generate` | Search, then an LLM writes the answer with sources | `LITELLM_KEY` |

Without a key, `rag-generate` returns an error and `rag-search` works as normal.

## Use your own docs

Drop markdown files into `data/docs/` and run `make kb`. Details in [UPDATING_THE_KB](docs/UPDATING_THE_KB.md).

## Layout

```
src/          config, retrieval, MCP server, entry point
scripts/      build_kb.py (chunk and embed)
data/         sample docs and the built knowledge base
config/       default.json, production.json
deployment/   Dockerfile, Kubernetes manifest
tests/        unit tests and an MCP stdio round trip
docs/         architecture, KB updates
examples/     MCP client config
```

More in [ARCHITECTURE](docs/ARCHITECTURE.md).

## Develop

```bash
pip install -r requirements-dev.txt
make test
```

## Deploy

```bash
make docker-build IMAGE=your-registry/rag-mcp:1.0.0
make k8s-deploy
```

The manifest expects a `rag-secrets` secret with `litellm-key` and a `rag-kb-data` ConfigMap holding the KB file.

## License

MIT
