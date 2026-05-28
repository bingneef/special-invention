from pydantic import BaseModel


class ActivityDocumentBase(BaseModel):
    document_id: str


class ActivityDocumentPayload(ActivityDocumentBase):
    artifact_uri: str


class ActivityDocumentsPayload(ActivityDocumentBase):
    artifact_uris: list[str]


class ActivityDocumentOutput(ActivityDocumentBase):
    artifact_uri: str


class ActivityDocumentsOutput(ActivityDocumentBase):
    artifact_uris: list[str]


# class IngestDocumentPayload(BaseModel):
#     document_id: str


# class IngestDocumentInput(BaseModel):
#     document_id: str


# class ConvertToDoclingPayload(BaseModel):
#     document_id: str


# class ConvertToDoclingOutput(BaseModel):
#     document_id: str
#     artifact_uri: str


# class DoclingToMarkdownPayload(BaseModel):
#     document_id: str
#     artifact_uri: str


# class DoclingToMarkdownOutput(BaseModel):
#     document_id: str
#     artifact_uri: str


# class DoclingToChunksPayload(BaseModel):
#     document_id: str
#     artifact_uri: str


# class DoclingToChunksOutput(BaseModel):
#     document_id: str
#     artifact_uris: list[str]


# class EmbedTextsPayload(BaseModel):
#     document_id: str
#     artifact_uris: list[str]


# class EmbedTextsOutput(BaseModel):
#     document_id: str
#     artifact_uris: list[str]


# class GenerateDocumentMetaPayload(BaseModel):
#     document_id: str
#     artifact_uri: str


# class GenerateDocumentMetaOutput(BaseModel):
#     document_id: str
#     artifact_uri: str
