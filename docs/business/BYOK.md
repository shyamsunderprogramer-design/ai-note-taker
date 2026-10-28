# Local AI and API keys (BYOK)

Use Ollama on your machine or supply your own cloud provider credentials. ANT's source configuration supports both; cloud usage is charged by the provider to the account owning the key.

## Configure and use

1. Follow the [setup guide](../../README.md#set-up-from-source), including stable signing and encryption keys.
2. For local AI, run Ollama, download a model, and select its exact installed name in ANT. The default general model is `qwen3.5:9b`; individual modes can have their own environment overrides.
3. For cloud AI, open Settings, select a provider, paste the key, and save. Choose a model for that provider or Auto.
4. Verify a short typed question before testing voice, screenshots, or long context.
5. Screenshot requests require a vision-capable model. A valid text provider key alone does not enable image input.

The Settings save flow and the authenticated BYOK API are separate interfaces. Read their implementation before assuming identical validation behavior.

## Configuration and request flow

| Area | Source of truth |
| --- | --- |
| Backend defaults and environment variables | [Environment template](../../.env.example) and [config.py](../../backend/core/config.py) |
| UI provider selection and save | [app.js](../../apps/web/app.js) |
| Per-user credential storage | [user_api_keys.py](../../backend/modules/crm/user_api_keys.py) |
| Provider requests | [cloud_providers.py](../../backend/modules/platform/cloud_providers.py) |
| AI mode routing | [ai_router.py](../../backend/modules/ai/ai_router.py) |
| Authenticated BYOK endpoints | [ollama.py](../../backend/routes/ollama.py) |

User keys and server-wide environment keys serve different scopes. A key configured on a shared backend should not be treated as a private per-user key.

## BYOK API

These routes use the signed-in user's identity. Supply `Authorization: Bearer TOKEN` for status, configure, and delete.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/providers/byok/status` | Inspect configured providers |
| POST | `/providers/byok/configure` | Submit `provider` and `api_key` as form fields |
| DELETE | `/providers/byok/{provider}` | Remove the user's provider key |
| GET | `/providers/byok/costs` | Read the application's stored cost metadata |

The configure route accepts `openai`, `anthropic`, `google`, `xai`, `deepseek`, `groq`, `perplexity`, and `ollama_cloud`. Consult the running [API schema](http://127.0.0.1:8000/docs) for the request contract. Cost metadata is an application estimate; check your provider account for actual billing and current rates.

## Data and troubleshooting

Cloud requests send relevant prompt, conversation, resume, and screenshot context to the selected provider. Local inference needs downloaded models and a running Ollama service. Keep API keys and `.env` private, and configure spending limits in your provider account.

If a request fails, check the selected provider/model, credential validity, account permissions, quota, and network connectivity. If a local model fails, check `ollama list` and mode-specific environment settings. Restart the backend after editing `.env`.

## Product rationale

Local inference provides a path without cloud API billing; BYOK lets users choose a provider without ANT reselling model usage. Model speed, quality, hardware requirements, and costs vary. The original monetization ideas and adoption metrics are historical proposals, not implemented product commitments.

## Historical references

The overlapping source documents are preserved in one [dated reference record](../archive/byok.md). Use that record for original technical examples and planning context, not current setup or status.
