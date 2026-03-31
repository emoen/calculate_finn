"""
Multi-provider LLM rotation for free-tier calls.

Provider order: OpenRouter → Groq → Mistral → Hugging Face.
Within each provider, models rotate on 429 or failure.
Both rank_cars.py and compress_reviews.py use this module.
"""

import requests
import time
import json

# ── Provider keys ──
OPENROUTER_KEY = "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"
GROQ_KEY = "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"
MISTRAL_KEY = "ijBnvm7srH4ffjxOr3woQnSCJZnk8U9B"
HF_KEY = "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"

# ── Provider definitions ──
PROVIDERS = [
    {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key": OPENROUTER_KEY,
        "extra_headers": {
            "HTTP-Referer": "https://github.com/endrem/calculate_finn",
            "X-Title": "Finn Car Pipeline",
        },
        "ranking_models": [
            "arcee-ai/trinity-large-preview:free",
            "google/gemma-3-27b-it:free",
            "google/gemma-3-12b-it:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "qwen/qwen3.6-plus-preview:free",
            "nousresearch/hermes-3-llama-3.1-405b:free",
            "google/gemma-3-4b-it:free",
        ],
        "compress_models": [
            "arcee-ai/trinity-mini:free",
            "google/gemma-3-12b-it:free",
            "google/gemma-3-27b-it:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "qwen/qwen3.6-plus-preview:free",
            "google/gemma-3-4b-it:free",
            "meta-llama/llama-3.2-3b-instruct:free",
        ],
    },
    {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": GROQ_KEY,
        "extra_headers": {},
        "ranking_models": [
            "llama-3.3-70b-versatile",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "qwen/qwen3-32b",
            "openai/gpt-oss-120b",
            "moonshotai/kimi-k2-instruct",
        ],
        "compress_models": [
            "llama-3.3-70b-versatile",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "qwen/qwen3-32b",
            "openai/gpt-oss-20b",
            "moonshotai/kimi-k2-instruct",
        ],
    },
    {
        "name": "Mistral",
        "url": "https://api.mistral.ai/v1/chat/completions",
        "key": MISTRAL_KEY,
        "extra_headers": {},
        "ranking_models": [
            "mistral-small-latest",
            "open-mistral-nemo",
            "ministral-8b-latest",
        ],
        "compress_models": [
            "mistral-small-latest",
            "open-mistral-nemo",
            "ministral-8b-latest",
        ],
    },
    {
        "name": "HuggingFace",
        "url": "https://router.huggingface.co/v1/chat/completions",
        "key": HF_KEY,
        "extra_headers": {},
        "ranking_models": [
            "Qwen/Qwen2.5-72B-Instruct",
            "google/gemma-3-27b-it",
            "Qwen/QwQ-32B",
        ],
        "compress_models": [
            "Qwen/Qwen2.5-72B-Instruct",
            "google/gemma-3-27b-it",
            "Qwen/QwQ-32B",
        ],
    },
]

# ── Convenience lists for check_models.py ──
RANKING_MODELS = []
COMPRESS_MODELS = []
for p in PROVIDERS:
    RANKING_MODELS.extend(p["ranking_models"])
    COMPRESS_MODELS.extend(p["compress_models"])

# ── State tracking ──
_current_provider = {"ranking": 0, "compress": 0}
_current_model_idx = {"ranking": 0, "compress": 0}


def _get_provider(task):
    """Return the current provider dict for a task."""
    return PROVIDERS[_current_provider[task]]


def _get_models(task):
    """Return the model list for the current provider and task."""
    p = _get_provider(task)
    return p["ranking_models"] if task == "ranking" else p["compress_models"]


def get_current_model(task):
    """Return the current model name (for display purposes)."""
    models = _get_models(task)
    idx = _current_model_idx[task]
    if idx < len(models):
        return models[idx]
    return "exhausted"


def _rotate(task):
    """
    Advance to the next model or provider.
    Returns (provider_dict, model_name) or (None, None) if all exhausted.
    """
    models = _get_models(task)
    _current_model_idx[task] += 1

    # Still have models in current provider?
    if _current_model_idx[task] < len(models):
        model = models[_current_model_idx[task]]
        provider = _get_provider(task)
        print(f"  >> Rotating to model: {model} ({provider['name']})")
        return provider, model

    # Move to next provider
    _current_provider[task] += 1
    _current_model_idx[task] = 0

    if _current_provider[task] < len(PROVIDERS):
        provider = _get_provider(task)
        models = _get_models(task)
        model = models[0]
        print(f"  >> Switching to provider: {provider['name']} — model: {model}")
        return provider, model

    return None, None


def call_llm(task, messages, response_format=None, timeout=30, referer=None, title=None):
    """
    Call LLM with automatic model + provider rotation on 429/failure.

    Args:
        task: "ranking" or "compress"
        messages: list of message dicts
        response_format: optional, e.g. {"type": "json_object"}
        timeout: request timeout in seconds
        referer: HTTP-Referer header (used for OpenRouter)
        title: X-Title header (used for OpenRouter)

    Returns:
        Parsed JSON response body on success, or None on failure.
    """
    retries_per_model = 2

    while _current_provider[task] < len(PROVIDERS):
        provider = _get_provider(task)
        models = _get_models(task)

        if _current_model_idx[task] >= len(models):
            # No more models in this provider, advance
            provider, model = _rotate(task)
            if provider is None:
                break
            continue

        model = models[_current_model_idx[task]]

        headers = {
            "Authorization": f"Bearer {provider['key']}",
            "Content-Type": "application/json",
        }
        headers.update(provider.get("extra_headers", {}))
        if referer and "HTTP-Referer" not in headers:
            headers["HTTP-Referer"] = referer
        if title and "X-Title" not in headers:
            headers["X-Title"] = title

        payload = {
            "model": model,
            "messages": messages,
        }
        if response_format:
            payload["response_format"] = response_format

        for attempt in range(retries_per_model):
            try:
                response = requests.post(
                    provider["url"], headers=headers, json=payload, timeout=timeout
                )

                if response.status_code == 200:
                    return response.json()

                print(f"  API Error ({provider['name']}/{model}): {response.status_code} - {response.text[:200]}")

                # 429 = rate limited → rotate
                if response.status_code == 429:
                    provider, model = _rotate(task)
                    if provider is None:
                        print("  !! All providers and models exhausted. Stopping.")
                        return None
                    break  # break retry loop, try next model

                # Other 4xx = skip this model
                if 400 <= response.status_code < 500:
                    provider, model = _rotate(task)
                    if provider is None:
                        return None
                    break

                # 5xx = retry after delay
                time.sleep(2 * (attempt + 1))

            except Exception as e:
                if attempt == retries_per_model - 1:
                    print(f"  Error calling {provider['name']}: {e}")
                    provider, model = _rotate(task)
                    if provider is None:
                        return None
                    break
                time.sleep(2 * (attempt + 1))

    return None
