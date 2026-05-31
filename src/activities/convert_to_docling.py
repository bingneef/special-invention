from docling_core.types.doc.document import DoclingDocument
from temporalio import activity

from src.models import AppendArtifact
from src.services.docling import DoclingService
from src.services.s3 import S3Service
from src.workflows.contracts import ActivityDocumentOutput, ActivityDocumentPayload

default_s3_service = S3Service()
default_docling_service = DoclingService()


class ConvertToDoclingOutput(AppendArtifact):
    document_id: str
    docling_document: DoclingDocument


class ConvertToDocling:
    def __init__(self, s3_service=default_s3_service, docling_service=default_docling_service):
        self.s3_service = s3_service
        self.docling_service = docling_service

    @activity.defn
    async def convert_to_docling(
        self,
        payload: ActivityDocumentPayload,
    ) -> ActivityDocumentOutput:
        print(f"[ConvertToDocling] processing {payload.document_id}")

        # Note: it should come from S3, but since we mock it this is here for now.. (so we can start with an actual pdf)
        if payload.artifact_uri.startswith("s3://"):
            # Process data
            url = await self.s3_service.generate_presigned_url(
                bucket_name="my-bucket", artifact_name=payload.artifact_uri
            )
        else:
            url = payload.artifact_uri

        docling_content = await self.docling_service.convert_document(url)

        artifact_data = ConvertToDoclingOutput(
            document_id=payload.document_id, artifact_name="document.json", docling_document=docling_content
        )

        # Store data
        artifact_uri = await self.s3_service.store_artifact(
            bucket_name="my-bucket",
            artifact_name=f"{payload.document_id}/convert_to_docling/{artifact_data.artifact_name}",
            artifact_data=artifact_data,
        )

        return ActivityDocumentOutput(
            document_id=payload.document_id,
            artifact_uri=artifact_uri,
        )
