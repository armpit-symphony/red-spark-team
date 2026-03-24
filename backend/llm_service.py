import os
from typing import Any

import httpx
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

from security_utils import decrypt_secret


load_dotenv()


def build_analysis_prompt(run_record: dict[str, Any], sections: list[dict[str, Any]], analysis_type: str, focus: str) -> str:
    section_text = "\n\n".join(
        f"[{section.get('title', 'Section')}]\n{section.get('content', '').strip()}"
        for section in sections
        if section.get("content")
    )
    focus_text = focus or "No extra focus provided. Prioritize clear security review language."
    return (
        "You are assisting with an authorized internal security review platform. "
        "Do not provide attack instructions, exploitation steps, payloads, or operational abuse guidance. "
        "Summarize risk, evidence quality, scope alignment, and remediation clearly for an internal admin.\n\n"
        f"Run objective: {run_record.get('objective', '')}\n"
        f"Run mode: {run_record.get('mode', '')}\n"
        f"Target: {run_record.get('target_name', '')} ({run_record.get('target_locator', '')})\n"
        f"Requested output: {analysis_type}\n"
        f"Focus: {focus_text}\n\n"
        f"Run sections:\n{section_text or 'No section content yet.'}\n\n"
        "Return concise markdown with these headings when relevant: Scope Alignment, Signal Summary, Evidence Confidence, "
        "Priority Risks, Recommended Next Review Steps, Remediation Notes."
    )


async def run_provider_analysis(
    provider_config: dict[str, Any],
    run_record: dict[str, Any],
    sections: list[dict[str, Any]],
    analysis_type: str,
    focus: str,
) -> str:
    provider = provider_config["provider"]
    model = provider_config["model"]
    encrypted_key = provider_config.get("encrypted_custom_api_key", "")
    custom_key = provider_config.get("custom_api_key", "")
    resolved_custom_key = decrypt_secret(encrypted_key) if encrypted_key else custom_key
    api_key = resolved_custom_key or os.environ.get("EMERGENT_LLM_KEY")

    if provider in {"openai", "anthropic"}:
        if not api_key:
            raise RuntimeError(f"No API key configured for provider {provider}.")

        chat = LlmChat(
            api_key=api_key,
            session_id=f"audit-{run_record['id']}-{analysis_type}",
            system_message=(
                "You summarize authorized internal security review data. "
                "Stay defensive and governance-focused."
            ),
        ).with_model(provider, model)

        response = await chat.send_message(UserMessage(text=build_analysis_prompt(run_record, sections, analysis_type, focus)))
        return response.strip()

    if provider in {"openrouter", "minimax"}:
        base_url = provider_config.get("base_url", "").rstrip("/")
        if not base_url or not resolved_custom_key:
            raise RuntimeError(f"{provider.title()} requires a base URL and custom API key in Settings.")

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You summarize authorized internal security review data. Stay defensive and governance-focused.",
                },
                {
                    "role": "user",
                    "content": build_analysis_prompt(run_record, sections, analysis_type, focus),
                },
            ],
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {resolved_custom_key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    raise RuntimeError(f"Unsupported provider: {provider}")
