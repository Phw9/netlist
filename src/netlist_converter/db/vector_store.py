"""ChromaDB vector store for datasheet embeddings and RAG retrieval."""

from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from netlist_converter.llm.provider import LLMProvider

COLLECTION_NAME = "datasheets"
DEFAULT_N_RESULTS = 5


class VectorStore:
    """Wrapper around ChromaDB for storing and querying datasheet embeddings."""

    def __init__(self, persist_dir: Path, llm: LLMProvider) -> None:
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.Client(
            ChromaSettings(
                persist_directory=str(persist_dir),
                anonymized_telemetry=False,
                is_persistent=True,
            )
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._llm = llm

    def add_texts(self, texts: list[str], metadatas: list[dict] | None = None) -> list[str]:
        """Embed and store text chunks. Returns assigned IDs."""
        embeddings = self._llm.get_embeddings(texts)
        ids = [f"doc_{self._collection.count() + i}" for i in range(len(texts))]

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas or [{} for _ in texts],
        )
        return ids

    def query(self, query_text: str, n_results: int = DEFAULT_N_RESULTS) -> list[dict]:
        """Find the most similar stored documents to the query."""
        query_embedding = self._llm.get_embeddings([query_text])[0]

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        items: list[dict] = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            items.append({
                "document": doc,
                "metadata": meta,
                "distance": dist,
            })

        return items

    @property
    def count(self) -> int:
        return self._collection.count()
