import hashlib
import json
from pathlib import Path

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import httpx
    from docling_core.transforms.chunker.base import BaseChunk
    from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
    from docling_core.types.doc.document import DoclingDocument
    from pydantic import BaseModel
    from transformers import AutoTokenizer


class DoclingChunk(BaseModel):
    chunk_id: int
    content: str
    page: int | None


class DoclingService:
    def __init__(self, base_href: str = "http://0.0.0.0:5001"):
        self.base_href = base_href

    async def convert_document(self, document_uri: str):
        print(f"Converting document at {document_uri} using DoclingService...")
        url = "http://localhost:5001/v1/convert/source"

        # A cache for testing
        document_id = hashlib.sha256(document_uri.encode()).hexdigest()
        file_path = Path(f"./storage/docling/{document_id}.json")
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists():
            print(f"Document {document_id} already exists, skipping conversion.")
            with open(file_path, "r") as f:
                return DoclingDocument.model_validate(json.load(f))

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }

        payload = {
            "sources": [{"url": document_uri, "kind": "http"}],
            "options": {"to_formats": ["json", "md"]},
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.post(url, headers=headers, json=payload)

        print("Status code:", response.status_code)
        print("Response:", response.json())

        docling_content = response.json()["document"].get("json_content")

        with open(file_path, "w") as f:
            json.dump(docling_content, f)

        return DoclingDocument.model_validate(docling_content)

    def chunk_document(self, docling_document: DoclingDocument):
        # TODO: add previous / next chunk
        EMBED_MODEL_ID = "intfloat/multilingual-e5-large"
        tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_ID)
        tokenizer.model_max_length = 400
        tokenizer.truncation = True

        chunker = HybridChunker(tokenizer=tokenizer)
        # FIXME: Still issue with chunks too large!
        raw_chunks = list(chunker.chunk(dl_doc=docling_document))

        chunks = [
            DoclingChunk(
                chunk_id=i,
                content=chunker.contextualize(chunk),
                page=self._get_page_from_chunk(chunk),
            )
            for i, chunk in enumerate(raw_chunks)
        ]

        return chunks

    def _get_page_from_chunk(self, chunk: BaseChunk) -> int | None:
        # FIXME: Bad implementation
        try:
            return chunk.meta.doc_items[0].prov[0].page_no  # pyright: ignore[reportAttributeAccessIssue]
        except KeyError:
            print("[DoclingToChunks] No page number found for chunk, setting to None")
            return None
