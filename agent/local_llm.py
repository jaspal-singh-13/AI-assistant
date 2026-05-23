"""Local transformers pipeline wrapped as a LangChain BaseChatModel.

Used by build_llm() for OSS models when the HF Inference API is unavailable.
Model is loaded once and cached for the process lifetime.
"""

from __future__ import annotations

from typing import Any, Iterator, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

_PIPELINES: dict[str, Any] = {}


def _get_pipeline(model_name: str):
    if model_name not in _PIPELINES:
        from transformers import pipeline
        _PIPELINES[model_name] = pipeline(
            "text-generation",
            model=model_name,
            device="cpu",
            torch_dtype="auto",
        )
    return _PIPELINES[model_name]


def _to_hf_messages(messages: list[BaseMessage]) -> list[dict]:
    role_map = {HumanMessage: "user", AIMessage: "assistant", SystemMessage: "system"}
    result = []
    for msg in messages:
        role = role_map.get(type(msg), "user")
        result.append({"role": role, "content": str(msg.content)})
    return result


class LocalTransformersChatModel(BaseChatModel):
    model_name: str
    max_new_tokens: int = 512
    temperature: float = 0.7

    @property
    def _llm_type(self) -> str:
        return "local-transformers"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        pipe = _get_pipeline(self.model_name)
        hf_messages = _to_hf_messages(messages)
        output = pipe(
            hf_messages,
            max_new_tokens=self.max_new_tokens,
            do_sample=self.temperature > 0,
            temperature=self.temperature if self.temperature > 0 else None,
        )
        generated = output[0]["generated_text"]
        text = ""
        if isinstance(generated, list):
            for turn in reversed(generated):
                if isinstance(turn, dict) and turn.get("role") == "assistant":
                    text = turn.get("content", "")
                    break
        else:
            text = str(generated)

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        result = self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        text = result.generations[0].message.content
        yield ChatGenerationChunk(message=AIMessage(content=text))

    def bind_tools(self, tools: Any, **kwargs: Any) -> "LocalTransformersChatModel":
        # Qwen 0.5B doesn't support tool calling — return self unchanged so
        # create_react_agent can proceed; the model will never emit tool calls.
        return self
