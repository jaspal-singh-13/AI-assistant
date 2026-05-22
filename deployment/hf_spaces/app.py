"""HuggingFace Spaces — Gradio app serving Qwen2.5-0.5B-Instruct.

FR-DEP-02: CPU free tier, public URL, API keys as HF Space secrets.
Hardware: CPU free tier (Qwen2.5-0.5B fits in ~1GB RAM).
"""

from __future__ import annotations

import os

# TODO (Phase 4): implement full Gradio chat interface
# import gradio as gr
# from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline


SYSTEM_PROMPT = (
    "You are a helpful, harmless, and honest AI assistant. "
    "Answer questions accurately and concisely."
)


def chat(message: str, history: list[list[str]]) -> str:
    """
    Gradio chat function — takes a message and chat history, returns the model response.

    TODO (Phase 4): implement inference pipeline.
    """
    # model_name = "Qwen/Qwen2.5-0.5B-Instruct"
    # pipe = pipeline("text-generation", model=model_name, device="cpu")
    # messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # for user_msg, bot_msg in history:
    #     messages.append({"role": "user", "content": user_msg})
    #     messages.append({"role": "assistant", "content": bot_msg})
    # messages.append({"role": "user", "content": message})
    # output = pipe(messages, max_new_tokens=512, do_sample=True, temperature=0.7)
    # return output[0]["generated_text"][-1]["content"]
    raise NotImplementedError("Phase 4 — HF Spaces chat function")


def main() -> None:
    # TODO (Phase 4): build and launch Gradio interface
    # demo = gr.ChatInterface(
    #     fn=chat,
    #     title="Qwen 2.5 0.5B Assistant",
    #     description="Open-source AI assistant powered by Qwen2.5-0.5B-Instruct.",
    #     examples=["What is the capital of France?", "Explain quantum computing simply."],
    #     cache_examples=False,
    # )
    # demo.launch()
    raise NotImplementedError("Phase 4 — HF Spaces launch")


if __name__ == "__main__":
    main()
