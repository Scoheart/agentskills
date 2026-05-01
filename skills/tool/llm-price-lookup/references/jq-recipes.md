# JQ Recipes for Models.dev Pricing

## Broad search that preserves provider context

```bash
curl -s https://models.dev/api.json \
  | jq -r '
    to_entries[]
    | .key as $provider_id
    | .value as $provider
    | ($provider.models // {}) | to_entries[]
    | .value as $m
    | select(([$m.id, $m.name, .key, $provider_id, $provider.name] | map(. // "") | join(" ") | ascii_downcase | contains("glm-5.1")))
    | {
        provider: ($provider.name // $provider_id),
        provider_id: $provider_id,
        model_key: .key,
        model_id: $m.id,
        name: $m.name,
        input_per_1m: $m.cost.input,
        cache_read_per_1m: $m.cost.cache_read,
        cache_write_per_1m: $m.cost.cache_write,
        output_per_1m: $m.cost.output,
        context: $m.limit.context,
        output_limit: $m.limit.output
      }
  '
```

## Filter to a provider, such as Z.AI

```bash
curl -s https://models.dev/api.json \
  | jq -r '
    to_entries[]
    | select((.key + " " + (.value.name // "") | ascii_downcase) | test("zai|z-ai|z\\.ai"))
    | .key as $provider_id
    | .value as $provider
    | ($provider.models // {}) | to_entries[]
    | .value as $m
    | select(([$m.id, $m.name, .key] | map(. // "") | join(" ") | ascii_downcase | contains("glm-5.1")))
    | {
        provider: ($provider.name // $provider_id),
        provider_id: $provider_id,
        model_key: .key,
        model_id: $m.id,
        input_per_1m: $m.cost.input,
        cache_read_per_1m: $m.cost.cache_read,
        output_per_1m: $m.cost.output,
        context: $m.limit.context
      }
  '
```

## Recursive search for rough discovery only

```bash
curl -s https://models.dev/api.json \
  | jq '.. | objects | select(.id? and (.id | ascii_downcase | contains("glm-5.1")))'
```

This is useful for discovering possible ids, but it drops parent provider context. Do not use it as the final basis for pricing conclusions.

## OpenRouter exact id lookup

```bash
curl -s https://openrouter.ai/api/v1/models \
  | jq '.data[] | select(.id == "z-ai/glm-4.5-air:free") | {id, name, pricing, context_length}'
```
