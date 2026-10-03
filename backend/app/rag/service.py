"""Application-facing RAG facade, intentionally narrow and misconception-led."""

from app.rag.retriever import KnowledgeRetriever
from app.rag.schemas import RetrievalContext, RetrievalQuery


class RagService:
    def __init__(self, retriever: KnowledgeRetriever) -> None:
        self.retriever = retriever

    def retrieve_for_intervention(self, query: RetrievalQuery) -> RetrievalContext:
        results = list(self.retriever.retrieve(query))
        source_labels = list(dict.fromkeys(result.chunk.metadata.source for result in results))
        return RetrievalContext(query=query, results=results, source_labels=source_labels)
