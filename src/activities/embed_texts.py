import asyncio
from typing import Any

from pydantic import create_model
from temporalio import activity

from src.models import AppendArtifact
from src.services.ai import AIService
from src.services.s3 import S3Service
from src.workflows.contracts import ActivityDocumentsOutput, ActivityDocumentsPayload


class EmbedTextPayload(ActivityDocumentsPayload):
    field: str


class EmbedTextOutput(AppendArtifact):
    embedding: list[float]


default_s3_service = S3Service()
default_ai_service = AIService()


def get_embedding(text: str) -> list[float]:
    return [1.0, 2.0, 3.0]  # Dummy embedding for demonstration


class EmbedTexts:
    def __init__(self, s3_service=default_s3_service, ai_service=default_ai_service):
        self.s3_service = s3_service
        self.ai_service = ai_service

    @activity.defn
    async def embed_texts(self, payload: EmbedTextPayload) -> ActivityDocumentsOutput:
        print(f"[EmbedText] processing {payload.document_id}")
        fields: dict[str, Any] = {payload.field: (str, ...)}

        # Generate dynamic Pydantic model for artifact data based on the specified field
        EmbedTextPayload = create_model(
            "EmbedTextPayload",
            __base__=AppendArtifact,
            **fields,
        )

        # Fetch artifacts
        tasks = [self.s3_service.fetch_artifact(uri, model=EmbedTextPayload) for uri in payload.artifact_uris]
        artifacts = await asyncio.gather(*tasks)

        embeddings = await self.ai_service.generate_embeddings(
            [getattr(artifact, payload.field) for artifact in artifacts]
        )

        artifacts_datas = [
            EmbedTextOutput(
                **artifact.model_dump(),
                embedding=embedding,
            )
            for artifact, embedding in zip(artifacts, embeddings, strict=True)
        ]

        # FIXME: THIS IS A HACK! FIX IT!
        artifact_uris = [
            await self.s3_service.store_artifact(
                bucket_name="my-bucket",
                artifact_name=f"{payload.document_id}/embed_texts/f{artifact_data.artifact_name}",
                artifact_data=artifact_data,
            )
            for artifact_data in artifacts_datas
        ]

        return ActivityDocumentsOutput(document_id=payload.document_id, artifact_uris=artifact_uris)
