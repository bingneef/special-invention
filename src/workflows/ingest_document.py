import asyncio
from datetime import timedelta

from temporalio import workflow

from src.activities.convert_to_docling import ConvertToDocling
from src.activities.docling_to_chunks import DoclingToChunks
from src.activities.docling_to_markdown import DoclingToMarkdown
from src.activities.embed_texts import EmbedTextPayload, EmbedTexts
from src.activities.generate_document_meta import GenerateDocumentMeta
from src.activities.send_to_elastic import SendToElastic
from src.queues import AI_TASK_QUEUE, DOCUMENT_CONVERSION_TASK_QUEUE, ELASTIC_TASK_QUEUE
from src.workflows.contracts import (
    ActivityDocumentOutput,
    ActivityDocumentPayload,
    ActivityDocumentsPayload,
)


@workflow.defn
class IngestDocumentWorkflow:
    @workflow.run
    async def run(self, payload: ActivityDocumentPayload) -> ActivityDocumentOutput:
        document_id = payload.document_id

        result = await workflow.execute_activity(
            ConvertToDocling().convert_to_docling,
            ActivityDocumentPayload(document_id=document_id, artifact_uri=payload.artifact_uri),
            task_queue=DOCUMENT_CONVERSION_TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=5),
        )

        document_branch = asyncio.create_task(
            self._process_document_branch(document_id=document_id, docling_json_artifact_uri=result.artifact_uri)
        )
        chunk_branch = asyncio.create_task(
            self._process_chunk_branch(document_id=document_id, docling_json_artifact_uri=result.artifact_uri)
        )

        document_result, chunk_result = await asyncio.gather(document_branch, chunk_branch)

        result = await workflow.execute_activity(
            SendToElastic().send_to_elastic,
            ActivityDocumentsPayload(
                document_id=document_id, artifact_uris=[document_result.artifact_uri, *chunk_result.artifact_uris]
            ),
            task_queue=ELASTIC_TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=5),
        )

        return result

    async def _process_document_branch(self, document_id: str, docling_json_artifact_uri: str):
        result = await workflow.execute_activity(
            DoclingToMarkdown().docling_to_markdown,
            ActivityDocumentPayload(document_id=document_id, artifact_uri=docling_json_artifact_uri),
            task_queue=DOCUMENT_CONVERSION_TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=5),
        )

        result = await workflow.execute_activity(
            GenerateDocumentMeta().generate_document_meta,
            ActivityDocumentPayload(document_id=document_id, artifact_uri=result.artifact_uri),
            task_queue=AI_TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=5),
        )

        result = await workflow.execute_activity(
            EmbedTexts().embed_texts,
            EmbedTextPayload(document_id=document_id, artifact_uris=[result.artifact_uri], field="summary"),
            task_queue=AI_TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=5),
        )

        return ActivityDocumentPayload(document_id=document_id, artifact_uri=result.artifact_uris[0])

    async def _process_chunk_branch(self, document_id: str, docling_json_artifact_uri: str):
        result = await workflow.execute_activity(
            DoclingToChunks().docling_to_chunks,
            ActivityDocumentPayload(document_id=document_id, artifact_uri=docling_json_artifact_uri),
            task_queue=DOCUMENT_CONVERSION_TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=5),
        )

        result = await workflow.execute_activity(
            EmbedTexts().embed_texts,
            EmbedTextPayload(document_id=document_id, artifact_uris=result.artifact_uris, field="content"),
            task_queue=AI_TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=5),
        )

        return result
