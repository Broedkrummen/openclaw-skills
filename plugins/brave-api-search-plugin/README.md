# Brave API Search plugin

Native OpenClaw plugin by **Broedkrummen**, converted from the `brave-api-search` skill v4.2.0. Plugin version: **1.0.0**. License: **MIT-0**.

## Install

```bash
openclaw plugins install clawhub:brave-api-search-plugin
```

Requires OpenClaw 2026.9.8 or later and its supported Node.js runtime. Enable the plugin in OpenClaw if your install policy does not enable it automatically. The four tool names are declared in the manifest and follow your operator tool allow/deny policy.

## Credentials

Configure `plugins.entries.brave-api-search-plugin.config` with optional sensitive string fields `searchApiKey`, `answersApiKey`, `suggestApiKey`, and `spellcheckApiKey`, or set the environment variables in the OpenClaw Gateway environment. Credentials are checked when each tool is called; you do not need an Answers key to use Search.

| Tool | Credential fallback order |
| --- | --- |
| `brave_search` | `searchApiKey`, `BRAVE_SEARCH_API_KEY` |
| `brave_answers` | `answersApiKey`, `BRAVE_ANSWERS_API_KEY` |
| `brave_suggest` | `suggestApiKey`, `AUTOSUGGEST_API_KEY`, `BRAVE_AUTOSUGGEST_API_KEY`, configured/environment Search key |
| `brave_spellcheck` | `spellcheckApiKey`, `BRAVE_SPELLCHECK_API_KEY`, configured/environment Search key |

Get credentials at https://api-dashboard.search.brave.com. Keep them outside the plugin package. This plugin does not load arbitrary `.env` files or edit system configuration. Brave requests consume your plan's quota; rich suggestions and research may require additional plan access or cost.

## Tools

Each tool takes a required nonempty `query` and optional two-letter `country`. Results contain readable text in `content` and structured data in `details`. API and validation errors return `isError: true` without terminating OpenClaw.

- **brave_search**: `count` (1–20, default 10), `offset` (0–9, default 0), `freshness` (`pd`, `pw`, `pm`, `py`, date range), `extra_snippets`, `summary`, `result_filter`, `search_lang`, `ui_lang`, `safesearch` (`off`, `moderate`, `strict`; default moderate), `spellcheck`, `spellcheck_info`, `text_decorations`, `units`, `lat`, `long`, `timezone`, `city`, `state`, `postal_code`. Preserves web results, pagination metadata, news, videos, discussions, FAQ and infobox data. Summary is fetched whenever requested and Brave returns a summarizer key.
- **brave_suggest**: `count` (1–10, default 5), `rich` (default false). Caches identical requests for 60 seconds within the plugin instance, with a 256-entry bound.
- **brave_spellcheck**: spelling suggestions or confirmation that no correction is needed.
- **brave_answers**: `enable_citations` (default true), `enable_research` (default false), `enable_entities` (default false), `stream` (default true). Streaming is consumed internally and a complete answer is returned, including deduplicated sources, entities, and any usage/cost data Brave supplies. Citations and entities are parsed across chunk boundaries. Non-streaming extracts metadata when supplied, but full feature coverage requires streaming.

Only official `https://api.search.brave.com/res/v1` endpoints are called. Search parameters and optional geographic context are sent to Brave. Requests retry up to three times on network errors, HTTP 429 and 5xx, honor bounded Retry-After delays, and have a 120-second timeout per attempt. Cancellation is forwarded to network requests. Response content is external, untrusted data.

## Development

Source is plain ESM JavaScript; no build step or third-party runtime dependencies are needed beyond the OpenClaw host SDK. Run `npm test` with OpenClaw resolvable in your Node environment. Tests use mock responses and do not spend Brave credits.

The original skill remains available at https://clawhub.ai/broedkrummen/brave-api-search. This is a separate native plugin release with the same four tool capabilities.
