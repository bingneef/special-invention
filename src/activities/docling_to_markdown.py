from docling_core.types.doc.document import DoclingDocument
from temporalio import activity

from src.models import AppendArtifact
from src.services.s3 import S3Service
from src.workflows.contracts import ActivityDocumentOutput, ActivityDocumentPayload


class DoclingToChunksPayload(AppendArtifact):
    docling_document: DoclingDocument


class DoclingToMarkdownOutput(AppendArtifact):
    content: str


default_s3_service = S3Service()


class DoclingToMarkdown:
    def __init__(self, s3_service=default_s3_service):
        self.s3_service = s3_service

    @activity.defn
    async def docling_to_markdown(self, payload: ActivityDocumentPayload) -> ActivityDocumentOutput:
        print(f"[DoclingToMarkdown] processing {payload.document_id}")

        data = await self.s3_service.fetch_artifact(payload.artifact_uri, model=DoclingToChunksPayload)
        docling_document = DoclingDocument.model_validate(data.docling_document)

        artifact_data = DoclingToMarkdownOutput(**data.model_dump(), content=docling_document.export_to_markdown())

        artifact_uri = await self.s3_service.store_artifact(
            bucket_name="my-bucket",
            artifact_name=f"{payload.document_id}/docling_to_markdown/{artifact_data.artifact_name}.json",
            artifact_data=artifact_data,
        )

        return ActivityDocumentOutput(
            document_id=payload.document_id,
            artifact_uri=artifact_uri,
        )
