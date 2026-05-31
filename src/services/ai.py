import os
from typing import TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

T = TypeVar("T", bound=BaseModel)

LITE_LLM_HOST = os.getenv("LITE_LLM_HOST", "no-op")
LITE_LLM_API_KEY = os.getenv("LITE_LLM_API_KEY", "no-op")


class AIService:
    def __init__(self, model: str = "claude-sonnet-4-6"):
        pass

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        from pydantic_ai import Embedder
        from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.litellm import LiteLLMProvider

        _provider = LiteLLMProvider(
            api_base=LITE_LLM_HOST,
            api_key=LITE_LLM_API_KEY,
        )

        _model_anthropic = OpenAIChatModel(
            "anthropic:claude-haiku-4-5",
            provider=_provider,
        )
        _embedder_model = OpenAIEmbeddingModel("text-embedding-3-small", provider=_provider)

        self._model = _model_anthropic
        self._embedder = Embedder(_embedder_model)

        result = await self._embedder.embed_documents(texts)
        return [list(embedding) for embedding in result.embeddings]

    async def generate_chat_response(
        self,
        instructions: str | None,
        prompt: str,
        response_model: type[T],
    ) -> T:
        from pydantic_ai import Agent, Embedder
        from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.litellm import LiteLLMProvider

        _provider = LiteLLMProvider(
            api_base=LITE_LLM_HOST,
            api_key=LITE_LLM_API_KEY,
        )

        _model_anthropic = OpenAIChatModel(
            "anthropic:claude-sonnet-4-5",
            provider=_provider,
        )
        _embedder_model = OpenAIEmbeddingModel("text-embedding-3-small", provider=_provider)

        self._model = _model_anthropic
        self._embedder = Embedder(_embedder_model)

        agent = Agent(model=self._model, instructions=instructions, output_type=response_model)
        result = await agent.run(prompt)

        return result.output
