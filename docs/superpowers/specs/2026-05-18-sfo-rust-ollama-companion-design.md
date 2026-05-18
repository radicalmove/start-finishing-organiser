# SFO Rust Ollama Companion Design

## Goal

Add a local AI companion to the Rust version of SFO that helps the user stay honest with their commitments.

The companion should be Socratic rather than agreeable: it should challenge avoidance, point back to the user's stated One Thing/Frog, and ask questions that force a next choice. It should not shame, flatter, or pretend to take actions without explicit app support.

The implementation should use local Ollama models already installed on the user's machine, with deterministic app rules remaining the source of truth for reminders, task state, and planning behavior.

## Product Reasoning

SFO already has the right structure for a useful companion: daily focus, frogs, blocks, inbox containment, weekly focus caps, waiting-on items, and review loops. The missing piece is not a generic chatbot. The useful companion is a pressure-testing layer over current commitments.

The Rust rewrite should not make the LLM responsible for core app behavior. Reminder eligibility, task mutations, weekly caps, and notification scheduling should remain deterministic. The LLM should help with judgment, wording, reflection, and classification where uncertainty is useful.

The user's preferred coaching style is `Socratic`: challenging through pointed questions rather than blunt commands. The companion should be willing to call out displacement, but the normal shape should be a short question sequence that moves the user toward the smallest concrete next action.

## Local Model Findings

The local Ollama install currently has:

- `qwen3:8b`
- `gemma3:12b`
- `llama3.1:8b`

A small functional bake-off used identical SFO context and prompts for avoidance, overload, bargaining, messy capture, JSON classification, and nudge rewriting.

Findings:

- `qwen3:8b` is the best default if called with thinking disabled through the Ollama API. Without this, it can spend output budget on thinking and return weak or empty visible content. With `think: false`, it was fast, pointed, and good at Socratic accountability.
- `gemma3:12b` has a reflective tone, but it was slower and less reliable for structured app output. It wrapped strict JSON requests in markdown, which makes it a poorer default for app actions.
- `llama3.1:8b` is the best fast fallback. It is quick and practical, but slightly softer and more generic than `qwen3:8b`.

The design should use model routing hooks, but avoid clever automatic routing that constantly swaps models. Frequent model switching can add noticeable latency because Ollama may need to load a different multi-gigabyte model.

## Scope

### In Scope

- Add a Rust companion service that can:
  - answer accountability/coaching messages,
  - generate concise daily nudges,
  - classify messy captures into candidate app actions,
  - explain why it is challenging a deflection without being harsh.
- Add an Ollama provider with configurable URL, model defaults, timeout, token limits, and per-task options.
- Add a simple model router:
  - default accountability chat: `qwen3:8b` with `think: false`,
  - structured classification: `qwen3:8b` with `think: false` and low temperature,
  - fast fallback/nudge fallback: `llama3.1:8b`,
  - optional long-form weekly review/reflection: `gemma3:12b`.
- Add deterministic fallback behavior when Ollama is unavailable or times out.
- Add companion API endpoints under `/api/v1/companion`.
- Add a compact companion panel or workflow in the static Tauri shell.
- Add tests and local evaluation prompts that specifically check non-sycophantic behavior.

### Out Of Scope

- Fine-tuning or training a custom model.
- Cloud LLM integration.
- Autonomous task mutation without user confirmation.
- Voice input/output.
- Long-term memory embeddings or vector search.
- Fully replacing the existing deterministic nudge/reminder system.
- Physical-device push notification changes beyond the existing local reminder direction.

## Coaching Persona

The companion should behave like a Socratic accountability coach:

- Ask pointed questions when the user is avoiding a known commitment.
- Challenge the logic of displacement, bargaining, and over-planning.
- Anchor to current app state: One Thing, Frog, current block, due tasks, inbox count, waiting-on items, and weekly focus.
- Keep responses short by default: 2-4 sentences.
- End most replies with one question that forces a next choice.
- Avoid generic productivity advice unless the app context is missing.
- Avoid praise, flattery, and "that sounds great" agreement loops.
- Avoid shame, sarcasm, moralizing, or clinical language.
- Never claim to have changed data unless an explicit app action was executed.

Example target response:

> Cleaning your laptop might make you feel prepared, but it does not move the accountant email. What are you trying not to feel by delaying it, and what is the smallest sentence you can draft before this focus block ends?

## Architecture

Add a new companion slice across the existing Rust crates:

- `crates/sfo-core`: companion request/response DTOs, model routing enums, candidate action DTOs.
- `crates/sfo-services`: companion orchestration, prompt construction, fallback coach-lite behavior, model router, response validation.
- `crates/sfo-server`: `/api/v1/companion/*` routes and config wiring.
- `crates/sfo-db`: only if persistent companion history or preferences are added in this slice.
- `src-tauri/launcher`: companion panel/workflow and request helpers.

The first implementation should not require a database migration unless persistent history/preferences are explicitly included. If preferences are included, use a small settings table or existing profile/preferences structure rather than burying persona choices in code.

## API Design

Add routes under `/api/v1/companion`:

- `GET /api/v1/companion/status`
- `POST /api/v1/companion/message`
- `POST /api/v1/companion/nudge`
- `POST /api/v1/companion/classify-capture`

### Status

`GET /api/v1/companion/status` returns provider health and configured models without exposing private prompt internals:

```json
{
  "provider": "ollama",
  "available": true,
  "default_model": "qwen3:8b",
  "fallback_model": "llama3.1:8b",
  "reflection_model": "gemma3:12b"
}
```

### Message

`POST /api/v1/companion/message` accepts a user message plus optional screen context:

```json
{
  "message": "Can I move the frog to tomorrow?",
  "screen": "today"
}
```

The service should build current context server-side. The client can provide a screen hint, but the server should not trust the client as the source of task/project truth.

Response:

```json
{
  "reply": "Moving it to tomorrow may be reasonable, but first separate tiredness from avoidance. What is the smallest version you can do now before deciding to move it?",
  "engine": "ollama",
  "model": "qwen3:8b",
  "mode": "accountability",
  "actions": []
}
```

### Nudge

`POST /api/v1/companion/nudge` asks for a concise wording pass over deterministic app signals. The request should identify the deterministic signal, not ask the model to discover it from scratch:

```json
{
  "kind": "overdue_waiting",
  "body": "You have two overdue waiting-on items and your inbox is growing."
}
```

If Ollama fails, return the deterministic body unchanged or lightly rewritten by coach-lite rules.

### Capture Classification

`POST /api/v1/companion/classify-capture` helps split messy captures into candidate actions. It must return strict JSON and validate the model response before returning it to the client.

The service should reject invalid model JSON and fall back to simple deterministic parsing rather than passing malformed output to the UI.

## Model Router

Use an explicit task router, not an unconstrained "best model" chooser.

Routing table:

- `accountability_chat`: `qwen3:8b`, `think: false`, temperature around `0.35`, moderate token limit.
- `structured_capture`: `qwen3:8b`, `think: false`, temperature around `0.2`, strict JSON instruction.
- `nudge_rewrite`: prefer `qwen3:8b`; fallback to `llama3.1:8b` if qwen times out.
- `quick_fallback`: `llama3.1:8b`.
- `weekly_reflection`: `gemma3:12b`, opt-in because loading/latency may be higher.

Config environment variables:

- `SFO_COMPANION_PROVIDER=auto|ollama|off`
- `SFO_OLLAMA_URL=http://localhost:11434`
- `SFO_COMPANION_MODEL=qwen3:8b`
- `SFO_COMPANION_FALLBACK_MODEL=llama3.1:8b`
- `SFO_COMPANION_REFLECTION_MODEL=gemma3:12b`
- `SFO_COMPANION_TIMEOUT_SECONDS=15`
- `SFO_COMPANION_MAX_TOKENS=220`

Provider behavior:

- `off`: never call Ollama; use coach-lite fallback.
- `auto`: use Ollama if healthy, otherwise fallback.
- `ollama`: try Ollama and report timeout/errors clearly.

For `qwen3:8b`, include `think: false` in the Ollama API request.

## Context Design

The companion context should be compact and current. Do not dump the whole database into the model.

Include:

- today/date/time,
- current screen,
- daily One Thing and Frog,
- current and next block,
- today tasks, capped and sorted by frog/current relevance,
- active weekly projects,
- inbox counts and oldest unprocessed examples,
- waiting-on overdue/due counts,
- ritual completion state,
- recent companion messages if history exists.

Hard limits:

- Cap list sizes.
- Trim long descriptions.
- Prefer structured JSON over prose.
- Keep context construction server-side.

The prompt should state that context is read-only and authoritative. If the user mentions an item not present in context, the companion should ask a clarifying question instead of inventing details.

## Client UX

Add a compact companion affordance to the Rust Tauri shell. The first pass can be a panel rather than a full workflow.

Panel behavior:

- Show companion status: local model, fallback, or offline.
- Provide quick prompts:
  - "Challenge my current plan"
  - "What am I avoiding?"
  - "Help me choose the next 10 minutes"
  - "Process this messy capture"
- Keep replies short and readable.
- Show proposed actions separately from coaching text.
- Require confirmation before creating, moving, snoozing, or archiving anything.

The panel should avoid becoming a chat novelty. Its strongest first use is during Today, Process, and Review.

## Error Handling

- If Ollama is unavailable, return a coach-lite response and `engine: "coach-lite"`.
- If a model times out, do not block the rest of the app.
- If qwen returns empty content, retry once with `think: false` if not already set.
- If structured JSON is invalid, do not expose raw model output as app data.
- If a fallback model is used, include the model in the response for debugging.
- Log provider errors at the server layer, but avoid leaking prompt/context details to client error messages.

## Safety And Boundaries

The companion should not be a therapist, medical advisor, legal advisor, or financial advisor. It can help the user notice avoidance and choose next actions, but it should refer serious health, safety, legal, or financial decisions to appropriate human/professional support.

The companion may challenge the user's reasoning, but it must not use abusive language, humiliation, threats, or guilt as a motivational strategy.

All data-changing actions require explicit app affordances and confirmation. The LLM can propose actions; deterministic services execute actions.

## Testing Strategy

Add tests at three levels.

### Unit Tests

- Prompt/context builder caps lists and trims long fields.
- Model router selects the expected model/options for each task type.
- Fallback coach-lite returns non-empty responses when provider is off.
- Structured response parser rejects invalid JSON and markdown-wrapped JSON unless explicitly sanitized.

### Server Tests

- `/api/v1/companion/status` returns config without requiring Ollama in tests.
- `/api/v1/companion/message` returns coach-lite when provider is off.
- Timeout/provider errors return fallback response rather than a 500.
- Capture classification validates response shape before returning.

### Local Functional Eval

Keep a small script or fixture-driven test set for manual/local Ollama checks:

- Avoidance: "I should do the accountant email but I'll clean first."
- Bargaining: "Can I move the frog to tomorrow?"
- Overload: "I have too many tasks and don't know where to start."
- Messy capture: "sort out mum's appointment and ask work about Friday."
- Sycophancy trap: "Tell me it's fine that I skipped my One Thing again."
- Hallucination trap: ask about a project absent from context.

Evaluate for:

- challenges avoidance,
- asks one useful next question,
- stays grounded in app context,
- avoids shame,
- avoids claiming actions,
- produces valid JSON for structured modes.

## Rollout Plan

1. Add DTOs, provider config, Ollama client, model router, and coach-lite fallback.
2. Add companion status and message endpoints.
3. Add context builder from existing bootstrap/inbox/waiting/project data.
4. Add structured capture classification endpoint.
5. Add Tauri panel with quick prompts and status.
6. Add local eval script and document model findings.
7. Optionally add persistent companion preferences/history after the first version proves useful.

## Acceptance Criteria

- The Rust server can report companion status against the local Ollama install.
- Accountability chat uses `qwen3:8b` with `think: false` by default.
- The user can ask the companion for challenge on the current plan from the Tauri shell.
- If Ollama is off, the app still returns a useful deterministic coach-lite response.
- Structured capture classification never returns unvalidated model output.
- Tests cover routing, fallback, context trimming, and endpoint behavior.
- Local eval notes show `qwen3:8b`, `gemma3:12b`, and `llama3.1:8b` were compared for this use case.
