import asyncio
from datetime import datetime

from pydantic import BaseModel
from temporalio import activity

from src.models import AppendArtifact
from src.services.ai import AIService
from src.services.s3 import S3Service
from src.workflows.contracts import ActivityDocumentOutput, ActivityDocumentPayload


class DocumentMetaResponse(BaseModel):
    title: str
    publication_date: datetime
    summary: str
    keywords: list[str]


default_s3_service = S3Service()
default_ai_service = AIService()


class GenerateDocumentMetaPayload(AppendArtifact):
    content: str


class GenerateDocumentMetaOutput(AppendArtifact):
    title: str
    publication_date: datetime | None
    summary: str
    keywords: list[str]


class GenerateDocumentMeta:
    def __init__(self, s3_service=default_s3_service, ai_service=default_ai_service):
        self.s3_service = s3_service
        self.ai_service = ai_service

    @activity.defn
    async def generate_document_meta(self, payload: ActivityDocumentPayload) -> ActivityDocumentOutput:
        print(f"[GenerateDocumentMeta] processing {payload.document_id}")

        # Fetch data
        data = await self.s3_service.fetch_artifact(payload.artifact_uri, model=GenerateDocumentMetaPayload)

        # Process data
        await asyncio.sleep(1)  # Mock
        output = await AIService().generate_chat_response(
            instructions="Write a concise summary and extract the required data from the following document content.",
            prompt=data.content,
            response_model=DocumentMetaResponse,
        )

        artifact_data = GenerateDocumentMetaOutput(
            **data.model_dump(),
            title=output.title,
            publication_date=output.publication_date,
            summary=output.summary,
            keywords=output.keywords,
        )
        # Store the data
        artifact_uri = await self.s3_service.store_artifact(
            bucket_name="my-bucket",
            artifact_name=f"{payload.document_id}/generate_document_meta/{artifact_data.artifact_name}",
            artifact_data=artifact_data,
        )

        return ActivityDocumentOutput(document_id=payload.document_id, artifact_uri=artifact_uri)
