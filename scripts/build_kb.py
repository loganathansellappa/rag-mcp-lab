"""Build the knowledge base: chunk markdown files, embed them, write one JSON file.

    python scripts/build_kb.py [--docs data/docs] [--out data/knowledge_base.json]

Each markdown file is split on headings. Each chunk is embedded locally with
fastembed, so no text leaves your machine.
"""

import argparse
import json
import re
from pathlib import Path

MODEL_NAME = "BAAI/bge-small-en-v1.5"
HEADING = re.compile(r"^(#{1,6})\s+(.+)$")


def chunk_markdown(path: Path) -> list[dict]:
    """Split one markdown file into chunks, one per heading section."""
    chunks, heading, lines = [], path.stem, []

    def flush():
        text = "\n".join(lines).strip()
        if text:
            chunks.append({"source": path.name, "heading": heading, "text": text})

    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING.match(line)
        if match:
            flush()
            heading, lines = match.group(2), [line]
        else:
            lines.append(line)
    flush()
    return chunks


def embed(chunks: list[dict]) -> list[dict]:
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name=MODEL_NAME)
    vectors = model.embed([c["text"] for c in chunks])
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        chunk["id"] = i
        chunk["embedding"] = [round(float(x), 5) for x in vector]
    return chunks


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--docs", type=Path, default=root / "data" / "docs")
    parser.add_argument("--out", type=Path, default=root / "data" / "knowledge_base.json")
    args = parser.parse_args()

    chunks = []
    for path in sorted(args.docs.glob("*.md")):
        found = chunk_markdown(path)
        print(f"{path.name}: {len(found)} chunks")
        chunks.extend(found)
    if not chunks:
        raise SystemExit(f"No markdown files found in {args.docs}")

    chunks = embed(chunks)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"model": MODEL_NAME, "chunks": chunks}, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Wrote {len(chunks)} chunks ({len(chunks[0]['embedding'])} dims) to {args.out}")


if __name__ == "__main__":
    main()
