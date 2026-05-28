from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIService:
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.model = model

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 2.0, 3.0] for _ in texts]

    async def generate_chat_response(
        self,
        prompt: str,
        response_model: type[T],
    ) -> T:
        return response_model(
            summary=f"Response to '{prompt}' using model {self.model}",
            keywords=["keyword1", "keyword2"],
        )
