from pydantic import BaseModel


class ElasticChunk(BaseModel):
    chunk_id: str
    content: str
    embedding: list[float]
    page: int | None


class ElasticDocument(BaseModel):
    document_id: str
    title: str
    content: str
    summary: str
    keywords: list[str]
    embedding: list[float]
    chunks: list[ElasticChunk]


class ElasticApiService:
    def __init__(self, base_href: str = "http://localhost:3000"):
        self.base_href = base_href

    async def store_document(self, document: ElasticDocument) -> bool:
        print(document)
        return True
