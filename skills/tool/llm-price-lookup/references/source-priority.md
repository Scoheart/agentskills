# Source Priority for LLM Pricing

Use this guide when interpreting LLM pricing from multiple sources.

## 1. Official provider pages

Official provider pricing pages are the source of truth for direct API billing. Use them when the user asks for "official" prices or when aggregator data conflicts.

Important official concepts to check:

- input tokens
- output tokens
- cached input / cache read tokens
- cache write or cache storage
- batch or flex discounts
- reasoning token billing
- image, audio, video, search, file, and code tool pricing
- region or enterprise pricing

## 2. OpenRouter exact id

OpenRouter is authoritative for OpenRouter billing, but not necessarily for direct provider billing.

Rules:

- Match the full id exactly before fuzzy matching.
- Treat suffixes as meaningful: `:free`, `:online`, `:beta`, `:extended`, `:thinking`.
- Do not strip suffixes unless explicitly comparing variants.
- A free alias can be temporary or rate-limited; mention preview/availability caveats when known.

## 3. Models.dev provider entries

Models.dev is useful for provider-by-provider comparison, but each row belongs to a specific provider.

Rules:

- Preserve `provider_id` and provider name.
- Same model family can have many rows and many prices.
- Do not call a row official unless the provider is the model vendor or an official first-party endpoint.
- Models.dev missing data does not mean the price is zero.

## 4. Community registries

LiteLLM, tokencost, and similar registries are useful for engineering cost estimation. Treat them as secondary unless the user's system uses that registry for billing or cost calculations.

## Common mistakes

- Using a recursive `.id` search result without parent provider context.
- Treating third-party provider prices as official vendor prices.
- Treating missing data as free.
- Applying standard model price to an OpenRouter `:free` alias.
- Applying `:free` alias price to the standard model.
- Ignoring cache read/cache write fields in cost logs.
