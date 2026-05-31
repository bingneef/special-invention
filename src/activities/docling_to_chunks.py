from docling_core.types.doc.document import DoclingDocument
from temporalio import activity

from src.models import AppendArtifact
from src.services.docling import DoclingService
from src.services.s3 import S3Service
from src.workflows.contracts import ActivityDocumentPayload, ActivityDocumentsOutput


class DoclingToChunksPayload(AppendArtifact):
    docling_document: DoclingDocument


default_s3_service = S3Service()
default_docling_service = DoclingService()


class DoclingToChunksChunkOutput(AppendArtifact):
    chunk_id: int
    document_id: str
    content: str
    page: int | None
    artifact_name: str


class DoclingToChunks:
    def __init__(self, s3_service=default_s3_service, docling_service=default_docling_service):
        self.s3_service = s3_service
        self.docling_service = docling_service

    @activity.defn
    async def docling_to_chunks(self, payload: ActivityDocumentPayload) -> ActivityDocumentsOutput:
        print(f"[DoclingToChunks] processing {payload.document_id}")

        # Fetch data
        data = await self.s3_service.fetch_artifact(payload.artifact_uri, model=DoclingToChunksPayload)
        docling_document = DoclingDocument.model_validate(data.docling_document)

        # Process data
        chunks = self.docling_service.chunk_document(docling_document)

        artifact_datas = [
            DoclingToChunksChunkOutput(
                chunk_id=chunk.chunk_id,
                document_id=payload.document_id,
                content=chunk.content,
                page=chunk.page,
                artifact_name=f"artifact_chunk_{chunk.chunk_id}.json",
            )
            for chunk in chunks
        ]

        # Store data
        artifact_uris = [
            await self.s3_service.store_artifact(
                bucket_name="my-bucket",
                artifact_name=f"{payload.document_id}/docling_to_chunks/{artifact_data.artifact_name}",
                artifact_data=artifact_data,
            )
            for artifact_data in artifact_datas
        ]

        return ActivityDocumentsOutput(
            document_id=payload.document_id,
            artifact_uris=artifact_uris,
        )
