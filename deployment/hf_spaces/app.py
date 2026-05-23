"""HuggingFace Spaces — Gradio app serving Qwen2.5-0.5B-Instruct.

FR-DEP-02: CPU free tier, public URL, API keys as HF Space secrets.
Hardware: CPU free tier (Qwen2.5-0.5B fits in ~1GB RAM).
"""

from __future__ import annotations

import os

import gradio as gr
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

SYSTEM_PROMPT = (
    "You are a helpful, harmless, and honest AI assistant. "
    "Answer questions accurately and concisely."
)

_MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
_pipe = None


def _get_pipeline():
    global _pipe
    if _pipe is None:
        _pipe = pipeline(
            "text-generation",
            model=_MODEL_NAME,
            device="cpu",
            torch_dtype="auto",
        )
    return _pipe


def chat(message: str, history: list[list[str]]) -> str:
    """Gradio chat function — takes a message and chat history, returns model response."""
    pipe = _get_pipeline()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for user_msg, bot_msg in (history or []):
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": bot_msg})
    messages.append({"role": "user", "content": message})

    output = pipe(messages, max_new_tokens=512, do_sample=True, temperature=0.7)
    # Extract the last generated assistant turn
    generated = output[0]["generated_text"]
    if isinstance(generated, list):
        for turn in reversed(generated):
            if turn.get("role") == "assistant":
                return turn.get("content", "")
    return str(generated)


def main() -> None:
    demo = gr.ChatInterface(
        fn=chat,
        title="Qwen 2.5 0.5B Assistant",
        description="Open-source AI assistant powered by Qwen2.5-0.5B-Instruct.",
        examples=[
            "What is the capital of France?",
            "Explain quantum computing in simple terms.",
            "Write a short poem about the ocean.",
        ],
        cache_examples=False,
    )
    demo.launch()


if __name__ == "__main__":
    main()
