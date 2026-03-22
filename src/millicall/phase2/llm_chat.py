"""LLM conversation service supporting multiple providers."""

import logging
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
            self.messages = self.messages[-self.max_history:]


async def chat_google(
    user_text: str,
    context: ConversationContext,
    system_prompt: str,
    api_key: str,
    model: str = "gemini-2.0-flash-lite",
) -> str:
    """Generate response using Google Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # Build contents array
    contents = []
    for msg in context.messages:
        contents.append({
            "role": "user" if msg.role == "user" else "model",
            "parts": [{"text": msg.content}],
        })
    contents.append({
        "role": "user",
        "parts": [{"text": user_text}],
    })

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_prompt}],
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 500,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        return "申し訳ございません、応答を生成できませんでした。"

    text = candidates[0]["content"]["parts"][0]["text"]
    logger.info("LLM response: '%s...'", text[:80])
    return text


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
) -> str:
    """Route to the appropriate LLM provider."""
    if provider == "google":
        return await chat_google(user_text, context, system_prompt, api_key, model)
    elif provider == "openai":
        return await chat_openai(user_text, context, system_prompt, api_key, model)
    elif provider == "anthropic":
        return await chat_anthropic(user_text, context, system_prompt, api_key, model)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
