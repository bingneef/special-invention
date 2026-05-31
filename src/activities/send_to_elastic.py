from pydantic.main import BaseModel
from temporalio import activity

from src.services.elastic_api import ElasticApiService, ElasticChunk, ElasticDocument
from src.services.s3 import S3Service
from src.workflows.contracts import ActivityDocumentOutput, ActivityDocumentsPayload

default_s3_service = S3Service()
default_elastic_api_service = ElasticApiService()


class DocumentPayload(BaseModel):
    title: str
    content: str
    summary: str
    keywords: list[str]
    embedding: list[float]


class ChunkPayload(BaseModel):
    chunk_id: int
    content: str
    embedding: list[float]
    page: int | None


class SendToElastic:
    def __init__(self, s3_service=default_s3_service, elastic_api_service=default_elastic_api_service):
        self.s3_service = s3_service
        self.elastic_api_service = elastic_api_service

    @activity.defn
    async def send_to_elastic(self, payload: ActivityDocumentsPayload) -> ActivityDocumentOutput:
        print(f"[SendToElastic] processing {payload.document_id}")

        # Fetch data
        document_artifact_uri, *chunk_artifact_uris = payload.artifact_uris
        document_data = await self.s3_service.fetch_artifact(document_artifact_uri, model=DocumentPayload)
        chunk_datas = [
            await self.s3_service.fetch_artifact(chunk_artifact_uri, model=ChunkPayload)
            for chunk_artifact_uri in chunk_artifact_uris
        ]

        # Process data
        data = ElasticDocument(
            document_id=payload.document_id,
            chunks=[
                ElasticChunk(
                    chunk_id=str(chunk_data.chunk_id),
                    content=chunk_data.content,
                    embedding=chunk_data.embedding,
                    page=chunk_data.page,
                )
                for chunk_data in chunk_datas
            ],
            title=document_data.title,
            content=document_data.content,
            summary=document_data.summary,
            keywords=document_data.keywords,
            embedding=document_data.embedding,
        )

        await self.elastic_api_service.store_document(data)

        # Store data
        artifact_uri = await self.s3_service.store_artifact(
            bucket_name="my-bucket",
            artifact_name=f"{payload.document_id}/send_to_elastic/artifact.json",
            artifact_data=data,
        )

        return ActivityDocumentOutput(
            document_id=payload.document_id,
            artifact_uri=artifact_uri,
        )
