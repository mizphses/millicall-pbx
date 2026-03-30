"""LLM conversation service supporting multiple providers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncio
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str


@dataclass
class ConversationContext:
    messages: list[ChatMessage] = field(default_factory=list)
    max_history: int = 10

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(ChatMessage(role=role, content=content))
        # Trim to max history
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history :]


def _build_google_payload(
    user_text: str,
    context: ConversationContext,
    system_prompt: str,
) -> dict:
    contents = []
    for msg in context.messages:
        contents.append(
            {
                "role": "user" if msg.role == "user" else "model",
                "parts": [{"text": msg.content}],
            }
        )
    contents.append({"role": "user", "parts": [{"text": user_text}]})
    return {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"temperature": 0.7},
    }


def _resolve_google_url(
    api_key: str, model: str, google_auth: object | None, stream: bool = False,
) -> tuple[str, dict[str, str]]:
    from millicall.infrastructure.google_auth import GoogleAuth

    action = "streamGenerateContent" if stream else "generateContent"
    if isinstance(google_auth, GoogleAuth):
        return google_auth.gemini_url(model=model, action=action)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta"
        f"/models/{model}:{action}?key={api_key}"
    )
    if stream:
        url += "&alt=sse"
    return url, {}


async def chat_google(
    user_text: str,
    context: ConversationContext,
    system_prompt: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
    google_auth: object | None = None,
) -> str:
    """Generate response using Google Gemini API (non-streaming)."""
    payload = _build_google_payload(user_text, context, system_prompt)
    url, headers = _resolve_google_url(api_key, model, google_auth, stream=False)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        blocked = data.get("promptFeedback", {}).get("blockReason", "")
        logger.error("Gemini returned no candidates. blockReason=%s", blocked)
        return "申し訳ございません、応答を生成できませんでした。"

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason", "")
    content = candidate.get("content", {})
    parts = content.get("parts", [])
    if not parts:
        logger.error("Gemini returned empty parts. finishReason=%s", finish_reason)
        return "申し訳ございません、応答を生成できませんでした。"

    text = parts[0].get("text", "")
    if finish_reason not in ("STOP", ""):
        logger.warning("Gemini incomplete (%s): '%s'", finish_reason, text[:100])
    logger.info("LLM response (%s): '%s...'", finish_reason, text[:80])
    return text


async def chat_google_streaming(
    user_text: str,
    context: ConversationContext,
    system_prompt: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
    google_auth: object | None = None,
    on_first_sentence: asyncio.Future[str] | None = None,
) -> str:
    """Stream Gemini response. Sets on_first_sentence when first sentence is ready."""
    import json as _json
    import re

    payload = _build_google_payload(user_text, context, system_prompt)
    # Use alt=sse for Server-Sent Events format
    url, headers = _resolve_google_url(api_key, model, google_auth, stream=True)
    if "?" in url:
        url += "&alt=sse"
    else:
        url += "?alt=sse"

    full_text = ""
    first_sent = False

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if not data_str:
                        continue

                    try:
                        chunk = _json.loads(data_str)
                    except _json.JSONDecodeError:
                        continue

                    candidates = chunk.get("candidates", [])
                    if not candidates:
                        continue
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts:
                        continue

                    text_chunk = parts[0].get("text", "")
                    full_text += text_chunk

                    # Signal first sentence as soon as we have one
                    if not first_sent and on_first_sentence and re.search(r"[。！？\n]", full_text):
                        match = re.search(r"^(.*?[。！？\n])", full_text)
                        if match and not on_first_sentence.done():
                            on_first_sentence.set_result(match.group(1).strip())
                            first_sent = True
    except Exception as exc:
        logger.error("Gemini streaming error: %s", exc)
        if on_first_sentence and not on_first_sentence.done():
            on_first_sentence.set_result("")

    # If we never found a sentence boundary, send everything
    if on_first_sentence and not on_first_sentence.done():
        on_first_sentence.set_result(full_text.strip())

    logger.info("LLM streaming response: '%s...'", full_text[:80])
    return full_text.strip()


async def chat_openai(
    user_text: str,
    context: ConversationContext,
    system_prompt: str,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> str:
    """Generate response using OpenAI Chat API."""
    url = "https://api.openai.com/v1/chat/completions"

    messages = [{"role": "system", "content": system_prompt}]
    for msg in context.messages:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    text = data["choices"][0]["message"]["content"]
    logger.info("OpenAI response: '%s...'", text[:80])
    return text


async def chat_anthropic(
    user_text: str,
    context: ConversationContext,
    system_prompt: str,
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """Generate response using Anthropic Claude API."""
    url = "https://api.anthropic.com/v1/messages"

    messages = []
    for msg in context.messages:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": model,
        "max_tokens": 500,
        "system": system_prompt,
        "messages": messages,
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    text = data["content"][0]["text"]
    logger.info("Anthropic response: '%s...'", text[:80])
    return text


async def generate_response(
    user_text: str,
    context: ConversationContext,
    system_prompt: str,
    provider: str,
    api_key: str,
    model: str,
    google_auth: object | None = None,
) -> str:
    """Route to the appropriate LLM provider."""
    if provider == "google":
        return await chat_google(
            user_text, context, system_prompt, api_key, model, google_auth=google_auth
        )
    elif provider == "openai":
        return await chat_openai(user_text, context, system_prompt, api_key, model)
    elif provider == "anthropic":
        return await chat_anthropic(user_text, context, system_prompt, api_key, model)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
