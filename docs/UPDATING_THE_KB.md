# Updating the knowledge base

Put markdown files in `data/docs/`, then rebuild:

```bash
make kb
```

That chunks every file on its headings, embeds each chunk, and rewrites `data/knowledge_base.json`. Restart the server to load it.

## When to rebuild

Rebuild when documents change. Do not rebuild on a schedule, the output is deterministic for the same input. The first run downloads the embedding model, about 50 MB, later runs reuse it.

## Chunking tips

Chunks follow your headings, so write one idea per section. A chunk that is a few short paragraphs retrieves best. Very long sections dilute the match, split them with a heading.

## Using your own corpus

```bash
python scripts/build_kb.py --docs path/to/docs --out data/knowledge_base.json
```

Point the service at a different file with `RAG_KB_PATH`.

## Check the result

```bash
python -c "import json; d=json.load(open('data/knowledge_base.json')); print(len(d['chunks']), 'chunks,', len(d['chunks'][0]['embedding']), 'dims')"
```
