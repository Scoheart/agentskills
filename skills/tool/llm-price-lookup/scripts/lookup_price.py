#!/usr/bin/env python3
"""Lookup LLM pricing from Models.dev and OpenRouter.

The script preserves provider context because model ids alone are ambiguous:
the same model family can have different prices across providers.

Examples:
  python scripts/lookup_price.py "glm-5.1"
  python scripts/lookup_price.py "z-ai/glm-4.5-air:free" --exact-openrouter
  python scripts/lookup_price.py "glm-5.1" --provider zai
  python scripts/lookup_price.py --self-test
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

MODELS_DEV_URL = "https://models.dev/api.json"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

OPENROUTER_ALIAS_SUFFIXES = (":free", ":online", ":beta", ":extended", ":thinking")

# Heuristic only. Always prefer official pages for final billing claims.
OFFICIAL_PROVIDER_HINTS = {
    "openai",
    "anthropic",
    "google",
    "google-vertex",
    "zai",
    "z-ai",
    "deepseek",
    "mistral",
    "xai",
    "moonshotai",
    "moonshotai-cn",
    "minimax",
    "minimax-cn",
    "groq",
    "cerebras",
    "fireworks",
    "cloudflare-workers-ai",
    "cloudflare-ai-gateway",
    "amazon-bedrock",
    "azure-openai-responses",
}


@dataclass
class LookupErrorInfo:
    source: str
    error: str


def fetch_json(url: str, timeout: int = 25) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "llm-price-lookup-skill/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def normalize(value: Any) -> str:
    return str(value or "").casefold()


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def openrouter_per_million(pricing: dict[str, Any], key: str) -> float | None:
    # OpenRouter prices are per token or per unit. Token prices need * 1,000,000.
    parsed = parse_float(pricing.get(key))
    if parsed is None:
        return None
    return parsed * 1_000_000


def likely_openrouter_id(query: str) -> bool:
    q = query.strip().lower()
    return "/" in q or any(suffix in q for suffix in OPENROUTER_ALIAS_SUFFIXES)


def match_text(query: str, parts: list[Any], exact: bool = False) -> bool:
    q = normalize(query)
    normalized_parts = [normalize(part) for part in parts]
    if exact:
        return any(part == q for part in normalized_parts)
    return q in " ".join(normalized_parts)


def search_models_dev(
    query: str,
    data: dict[str, Any],
    provider_filter: str | None = None,
    exact: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    provider_filter_norm = normalize(provider_filter)

    for provider_id, provider in data.items():
        if not isinstance(provider, dict):
            continue

        provider_name = provider.get("name") or provider_id
        if provider_filter_norm and provider_filter_norm not in normalize(f"{provider_id} {provider_name}"):
            continue

        models = provider.get("models") or {}
        if not isinstance(models, dict):
            continue

        for model_key, model in models.items():
            if not isinstance(model, dict):
                continue

            parts = [model_key, model.get("id"), model.get("name"), provider_id, provider_name]
            if not match_text(query, parts, exact=exact):
                continue

            cost = model.get("cost") or {}
            limit = model.get("limit") or {}
            provider_id_norm = normalize(provider_id)

            rows.append(
                {
                    "source": "models.dev",
                    "provider": provider_name,
                    "provider_id": provider_id,
                    "model_key": model_key,
                    "model_id": model.get("id"),
                    "name": model.get("name"),
                    "family": model.get("family"),
                    "official_provider_hint": provider_id_norm in OFFICIAL_PROVIDER_HINTS,
                    "input_per_1m": cost.get("input"),
                    "cache_read_per_1m": cost.get("cache_read"),
                    "cache_write_per_1m": cost.get("cache_write"),
                    "output_per_1m": cost.get("output"),
                    "context": limit.get("context"),
                    "input_limit": limit.get("input"),
                    "output_limit": limit.get("output"),
                    "tool_call": model.get("tool_call"),
                    "reasoning": model.get("reasoning"),
                    "open_weights": model.get("open_weights"),
                    "release_date": model.get("release_date"),
                    "last_updated": model.get("last_updated"),
                }
            )

    return sort_rows(rows, query)


def search_openrouter(query: str, data: dict[str, Any], exact: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    models = data.get("data") or []
    if not isinstance(models, list):
        return rows

    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = model.get("id") or ""
        model_name = model.get("name") or ""
        if not match_text(query, [model_id, model_name], exact=exact):
            continue

        pricing = model.get("pricing") or {}
        rows.append(
            {
                "source": "openrouter",
                "provider": "OpenRouter",
                "provider_id": "openrouter",
                "model_id": model_id,
                "name": model_name,
                "input_per_1m": openrouter_per_million(pricing, "prompt"),
                "cache_read_per_1m": openrouter_per_million(pricing, "input_cache_read"),
                "cache_write_per_1m": openrouter_per_million(pricing, "input_cache_write"),
                "output_per_1m": openrouter_per_million(pricing, "completion"),
                "request_cost": parse_float(pricing.get("request")),
                "image_cost": parse_float(pricing.get("image")),
                "web_search_cost": parse_float(pricing.get("web_search")),
                "internal_reasoning_per_1m": openrouter_per_million(pricing, "internal_reasoning"),
                "context": model.get("context_length"),
                "architecture": model.get("architecture"),
                "created": model.get("created"),
            }
        )

    return sort_rows(rows, query)


def sort_rows(rows: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    q = normalize(query)

    def score(row: dict[str, Any]) -> tuple[int, int, str, str]:
        exact = q in {
            normalize(row.get("model_id")),
            normalize(row.get("model_key")),
            normalize(row.get("name")),
        }
        official = bool(row.get("official_provider_hint"))
        provider = normalize(row.get("provider_id"))
        model_id = normalize(row.get("model_id"))
        return (0 if exact else 1, 0 if official else 1, provider, model_id)

    return sorted(rows, key=score)


def load_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    models_dev = {
        "zai": {
            "name": "Z.AI",
            "models": {
                "glm-5.1": {
                    "id": "glm-5.1",
                    "name": "GLM-5.1",
                    "family": "glm",
                    "tool_call": True,
                    "reasoning": True,
                    "cost": {"input": 1.4, "cache_read": 0.26, "output": 4.4},
                    "limit": {"context": 202752, "output": 131072},
                    "release_date": "2026-04-07",
                }
            },
        },
        "huggingface": {
            "name": "Hugging Face",
            "models": {
                "zai-org/GLM-5.1": {
                    "id": "zai-org/GLM-5.1",
                    "name": "GLM 5.1",
                    "family": "glm",
                    "tool_call": True,
                    "cost": {"input": 1.0, "output": 3.2},
                    "limit": {"context": 196608, "output": 65536},
                }
            },
        },
    }
    openrouter = {
        "data": [
            {
                "id": "z-ai/glm-4.5-air:free",
                "name": "Z.AI: GLM 4.5 Air (free)",
                "pricing": {"prompt": "0", "completion": "0"},
                "context_length": 131072,
            },
            {
                "id": "z-ai/glm-4.5-air",
                "name": "Z.AI: GLM 4.5 Air",
                "pricing": {"prompt": "0.00000013", "completion": "0.00000085"},
                "context_length": 131072,
            },
        ]
    }
    return models_dev, openrouter


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    errors: list[dict[str, str]] = []

    if args.self_test:
        models_dev_data, openrouter_data = load_fixture()
    else:
        models_dev_data = {}
        openrouter_data = {}
        try:
            models_dev_data = fetch_json(args.models_dev_url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            errors.append({"source": "models.dev", "error": str(exc)})
        try:
            openrouter_data = fetch_json(args.openrouter_url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            errors.append({"source": "openrouter", "error": str(exc)})

    exact_models_dev = bool(args.exact_models_dev)
    exact_openrouter = bool(args.exact_openrouter or likely_openrouter_id(args.query))

    models_dev_rows = (
        search_models_dev(args.query, models_dev_data, provider_filter=args.provider, exact=exact_models_dev)
        if models_dev_data
        else []
    )
    openrouter_rows = search_openrouter(args.query, openrouter_data, exact=exact_openrouter) if openrouter_data else []

    notes: list[str] = []
    if likely_openrouter_id(args.query):
        notes.append("query looks like an OpenRouter id; exact OpenRouter id matching was prioritized")
    if any(suffix in args.query.lower() for suffix in OPENROUTER_ALIAS_SUFFIXES):
        notes.append("alias suffix detected; do not strip the suffix unless comparing variants explicitly")
    if not models_dev_rows and models_dev_data:
        notes.append("no Models.dev match; this does not imply the model is free or unavailable")
    if not openrouter_rows and openrouter_data and likely_openrouter_id(args.query):
        notes.append("no exact OpenRouter match for the supplied id")

    return {
        "query": args.query,
        "provider_filter": args.provider,
        "models_dev_count": len(models_dev_rows),
        "openrouter_count": len(openrouter_rows),
        "models_dev": models_dev_rows[: args.limit],
        "openrouter": openrouter_rows[: args.limit],
        "notes": notes,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lookup LLM pricing with provider context.")
    parser.add_argument("query", nargs="?", help="Model name or provider/model id, e.g. glm-5.1")
    parser.add_argument("--provider", help="Filter Models.dev provider id/name, e.g. zai or huggingface")
    parser.add_argument("--exact-models-dev", action="store_true", help="Require exact model id/key/name match in Models.dev")
    parser.add_argument("--exact-openrouter", action="store_true", help="Require exact model id/name match in OpenRouter")
    parser.add_argument("--limit", type=int, default=50, help="Maximum rows per source to return")
    parser.add_argument("--models-dev-url", default=MODELS_DEV_URL)
    parser.add_argument("--openrouter-url", default=OPENROUTER_MODELS_URL)
    parser.add_argument("--self-test", action="store_true", help="Run against built-in fixture data instead of network")
    args = parser.parse_args(argv)

    if not args.query:
        parser.error("query is required unless testing a parser invocation")

    result = build_result(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
