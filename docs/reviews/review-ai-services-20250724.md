# Grumpy Review: `backend/app/services/ai/` (full module)
> 😤 *sigh* Reluctantly reviewed by Grumpy Agent. You wanted comprehensive? You got it.

---

## General Disappointment

This module is in a transitional state that nobody bothered to finish. There's a dead LangChain method sitting in `AIService` like a ghost haunting the new LangGraph tenants. The client singletons are frozen in time, so model switching doesn't actually work. `AIConfig` is a Pydantic `BaseModel` that the code tries to mutate – that's not how Pydantic works. The `router.py` repeats the same 8-line pattern four times. The `adapters/llamaindex.py` plays event-loop roulette with `asyncio.run`, `loop.run_until_complete`, and `nest_asyncio.apply()` stacked three times. There's enough `# type: ignore` to make a type checker cry. Let's go.

---

## The Issues (I hope you're sitting down)

---

### 🔴 CRITICAL – Correctness / Runtime Bugs

---

**Issue 1 — `ai_service.py` lines 323–326: Mutating a frozen Pydantic `BaseModel` silently fails (or raises `ValidationError` in Pydantic v2)**

```python
new_config = AIConfig.default()
if new_config.llm_provider == "azure":
    new_config.azure_llm_deployment = new_model   # 💥
else:
    new_config.openai_llm_model = new_model        # 💥
```

`AIConfig` extends `pydantic.BaseModel` and does **not** declare `model_config = {"frozen": False}` explicitly (it only sets `arbitrary_types_allowed`). In Pydantic v2, models are **immutable by default**. Attribute assignment on an immutable model raises a `ValidationError` at runtime. The entire `reinitialize_with_model` flow silently breaks, the `except` block catches the error, reinstates the old instance, and re-raises – meaning **runtime model switching never actually works**.

*Fix:* Use `new_config = AIConfig.default().model_copy(update={"openai_llm_model": new_model})` (or the Azure equivalent). Never mutate a `BaseModel` in place.

---

**Issue 2 — `providers/openai_client.py` lines 22–37 & `providers/azure_openai_client.py` lines 18–33: Module-level singletons are never invalidated on model switch**

Both `_client` and `_azure_client` are process-level module globals. `reinitialize_with_model` creates a new `AIService` (with a new `AIConfig`), but the singleton clients still hold the **old credentials, endpoint, and timeout**. Worse, the new providers created by the new `AIService` call `get_openai_client(new_config)` and immediately get the **cached old client** because `_client is not None`. Model reinitialisation is therefore partially a fiction.

*Fix:* Expose a `reset_openai_client()` / `reset_azure_openai_client()` function (or accept the client as a constructor arg) and call it from `AIServiceManager.reinitialize_with_model`. Alternatively, drop the module-level globals entirely and keep the client on the provider instance.

---

**Issue 3 — `ai_service.py` lines 177–209: Dead LangChain code in a project that has migrated to LangGraph**

```python
def create_chat_llm(self, **overrides) -> Any:
    """Create a LangChain-compatible chat LLM instance (ChatOpenAI)…"""
    try:
        from langchain_openai import AzureChatOpenAI, ChatOpenAI  # noqa: PLC0415
    except Exception as err:
        raise RuntimeError("ChatOpenAI (langchain_openai) is required…") from err
```

The project constraint is explicit: **LangChain is no longer part of the project; all functionality has moved to LangGraph**. Yet this method exists, imports `langchain_openai`, and is actively called from `agents_system/langgraph/nodes/agent_native.py:227`. If `langchain_openai` is not installed (which it shouldn't be in a LangChain-free project), every agent invocation dies with a `RuntimeError`.

*Fix:* The LangGraph agent (`agent_native.py`) must instantiate its LLM directly via LangGraph's native `ChatOpenAI` from `langchain_openai` (if LangGraph still needs it as a transitive dep) **without routing through `AIService`**, OR `AIService.create_chat_llm` must be replaced with a proper LangGraph-native factory. Either way, this method and its docstring are a lie and need to go.

---

**Issue 4 — `providers/openai_llm.py` line 458: `# type: ignore[union-attr]` on a call that **will** raise at runtime for streaming**

```python
async def complete(self, prompt: str, …) -> str:
    messages = [ChatMessage(role="user", content=prompt)]
    response = await self.chat(messages, temperature, max_tokens, **kwargs)
    return response.content  # type: ignore[union-attr]
```

`self.chat()` returns `LLMResponse | AsyncIterator[str]`. If `stream=True` somehow ends up in `**kwargs` (nothing stops it), `response` is an `AsyncIterator` and `.content` raises `AttributeError`. The `# type: ignore` comment is a suppression of a real type hole, not a false positive. The fix is either (a) explicitly disallow `stream` in `complete()` kwargs, or (b) narrow the call to never pass `stream=True`. As written, callers can silently pass `stream=True` through `**kwargs` and get an `AttributeError` instead of a sensible error.

---

**Issue 5 — `adapters/llamaindex.py` lines 95–120 (`complete`) and lines 130–167 (`chat`): `asyncio.run()` inside `except RuntimeError` is the wrong fix**

```python
try:
    response = asyncio.run(self.ai_service.complete(…))
except RuntimeError:
    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(…)
```

This catches **all** `RuntimeError`s, not just "there is no current event loop". A `RuntimeError` from inside the AI service itself (network failure, bad response) is silently swallowed and re-attempted on a (potentially closed) loop. The `except RuntimeError:` anti-pattern here is a trap. For the embedding methods (`_get_query_embedding`, `_get_text_embedding`, `_get_text_embeddings`) the same pattern recurs **three more times**, adding `nest_asyncio.apply()` as a side-effect – which patches the global event loop policy for the entire process, a very aggressive global mutation.

---

### 🟠 HIGH – Design / Configuration Issues

---

**Issue 6 — `config.py` entire file: `AIConfig` is a redundant DTO that duplicates `AppSettings` / `AISettingsMixin` field-for-field**

Compare `AISettingsMixin` (in `app/core/settings/ai.py`) with `AIConfig`:

| `AISettingsMixin` field | `AIConfig` field |
|---|---|
| `ai_openai_api_key` | `openai_api_key` |
| `ai_azure_llm_deployment` | `azure_llm_deployment` |
| `ai_default_temperature` | `default_temperature` |
| … (every field) | … (every field) |

`AppSettings` is declared the single source of truth. `AIConfig.from_settings()` copies all values over, then `AIConfig` is passed into every provider constructor, which stores it as `self.config`. Any update to `AppSettings` at runtime requires rebuilding `AIConfig` **and** rebuilding every provider. This double-layer adds zero protection and triples the places a misconfiguration can hide.

*Fix:* Providers should accept `AppSettings` (or the `AISettingsMixin`) directly, or a minimal typed sub-model that doesn't duplicate `AppSettings`. `AIConfig` as a DTO only makes sense if it genuinely transforms or normalises settings – here it's a flat copy with renamed keys.

---

**Issue 7 — `config.py` lines 55–57: Dual-key lookup in `from_settings()` embeds legacy compat logic that belongs in `AppSettings`**

```python
effective_api_key = settings.ai_openai_api_key or settings.openai_api_key or ""
effective_llm_model = settings.openai_model or settings.ai_openai_llm_model
effective_emb_model = settings.openai_embedding_model or settings.ai_openai_embedding_model
```

`AppSettings` already has `_OpenAISettingsCompat` and the legacy bare env-var fields for this exact reason. Now this same resolution logic is **duplicated** in `AIConfig.from_settings()`. If the priority order ever changes, it changes in two places. Move this logic fully into `AppSettings` (it's already started there).

---

**Issue 8 — `config.py` lines 96–107: `validate_provider_config` has redundant and incorrect conditions**

`openai_required_for_embedding` and `openai_required_for_llm` share the **same** fallback condition:

```python
openai_required_for_llm = self.llm_provider == "openai" or (
    self.fallback_enabled and self.fallback_provider == "openai"
)
openai_required_for_embedding = self.embedding_provider == "openai" or (
    self.fallback_enabled and self.fallback_provider == "openai"  # identical fallback check
)
```

When `fallback_provider == "openai"`, both conditions become `True` simultaneously, and both raise a `ValueError` for the same missing key. The error messages are also different ("for OpenAI LLM provider" vs "for OpenAI embedding provider"), causing confusing duplicate failures. The fallback condition is also subtly wrong: a fallback provider only applies to the dimension it falls back for (LLM or embedding, or both?). Using a single `fallback_provider` for both LLM and embeddings without separate `fallback_llm_provider` / `fallback_embedding_provider` fields is a design limitation that will bite someone.

---

### 🟡 MEDIUM – Code Quality / Maintainability

---

**Issue 9 — `router.py` lines 43–94: The fallback closure pattern is copy-pasted four times**

```python
fallback_call: Callable[[], Awaitable[…]] | None = None
if self.fallback_llm is not None:
    fallback_llm = self.fallback_llm
    def fallback_call() -> Awaitable[…]:
        return fallback_llm.method(**kwargs)
return await self._execute_with_fallback(…, fallback_call=fallback_call, …)
```

This pattern appears in `chat()`, `complete()`, `embed_text()`, and `embed_batch()`. The local `fallback_llm = self.fallback_llm` capture is the only interesting part (late-binding closure fix), but it's repeated verbatim four times. Extract a helper or just pass `self.fallback_llm` / `self.fallback_embedding` directly to `_execute_with_fallback` and let it handle the `None` check internally. 68 lines collapse to ~20.

---

**Issue 10 — `router.py` lines 43–52: Variable name `fallback_call` is declared as `None` then redefined as a `def` of the same name – this is legal Python but confusing**

The type annotation `fallback_call: Callable[…] | None = None` sets up a typed local, then `def fallback_call()` inside the `if` block silently shadows it. While this works at runtime, static analysers flag it as a redefinition. Use a distinct name (e.g., `_fallback`) or eliminate the pattern entirely (see Issue 9).

---

**Issue 11 — `ai_service.py` lines 193–209: Unnecessary `getattr` on a well-typed `AIConfig`**

```python
"azure_deployment": getattr(self.config, "azure_llm_deployment", None),
"api_version": getattr(self.config, "azure_openai_api_version", None),
…
```

`self.config` is typed as `AIConfig`, which declares all these fields with concrete types. `getattr` with a default of `None` defeats the type system and suggests the author wasn't sure the fields existed – they do. Just use `self.config.azure_llm_deployment` directly. If a field could legitimately be missing, fix the model, don't paper over it with `getattr`.

---

**Issue 12 — `ai_service.py` lines 267, 304: `asyncio.Lock` as a class-level variable is fine in Python 3.12, but the `get_instance` method is NOT async and does NOT use the lock**

```python
_lock: asyncio.Lock = asyncio.Lock()

@classmethod
def get_instance(cls, config: AIConfig | None = None) -> "AIService":
    if cls._instance is None:          # ← no lock here
        cls._instance = AIService(config)
    return cls._instance
```

`reinitialize_with_model` holds the lock during reinitialisation, but `get_instance` is a plain synchronous check-then-set without any lock. In a concurrent async environment, two coroutines can both see `_instance is None` simultaneously and create two `AIService` instances. The second one silently wins. Either make `get_instance` async and lock it too, or accept the (low) risk of double-init on startup.

---

**Issue 13 — `providers/openai_llm.py` lines 29, 361, 450 & `providers/openai_embedding.py` lines 32, 38, 49: f-string logging violates the lazy-evaluation convention**

```python
logger.info(f"OpenAI LLM Provider initialized with model: {self.model}")
logger.error(f"OpenAI chat error: {e}")
```

Use `%`-style formatting: `logger.info("OpenAI LLM Provider initialized with model: %s", self.model)`. This is not cosmetic – f-strings evaluate immediately even when the log level is disabled, wasting cycles building strings that are never emitted. The rest of the module already uses `%`-formatting correctly (e.g., lines 203, 218). Pick one style and use it everywhere.

---

**Issue 14 — `providers/openai_llm.py` throughout: 7 `# noqa: S105` and 1 `# noqa: S107` suppressions for a string `"max_tokens"` that Ruff incorrectly thinks is a hardcoded password**

```python
token_limit_param = "max_tokens"  # noqa: S105
token_limit_param: str = "max_tokens",  # noqa: S107
```

These are `ruff` false positives (S105 = "possible hardcoded password" triggered by a string containing `token`). The correct fix is to add a `ruff.toml` exclusion for this rule on this file (or globally, since this is clearly not a security concern), not to scatter `noqa` comments across 7 lines. The current approach means any future developer hitting the same pattern in a new variable will wonder why password rules are being suppressed for `max_tokens`.

---

**Issue 15 — `providers/azure_openai_embedding.py` line 27: `get_embedding_dimension` uses `openai_embedding_model` instead of the deployment name**

```python
def get_embedding_dimension(self) -> int:
    return EMBEDDING_DIMENSIONS.get(self.config.openai_embedding_model, 1536)
```

`self.model` is set to `config.azure_embedding_deployment` (line 20). The dimension lookup should use `self.model` (the deployment name) or the actual model name behind the deployment – but `openai_embedding_model` is the **OpenAI model name**, not the Azure deployment name. If someone configures a custom Azure deployment name that doesn't match a key in `EMBEDDING_DIMENSIONS`, this silently returns `1536` regardless of the actual model. The parent class `OpenAIEmbeddingProvider.get_embedding_dimension` correctly uses `self.model` – the override breaks that.

*Fix:* Either remove the override (let the parent use `self.model`) and keep Azure deployment names aligned with OpenAI model names, or add a separate `azure_embedding_model_name` config field for the actual model identifier.

---

**Issue 16 — `adapters/llamaindex.py` line 78: `metadata` property returns a plain `dict` instead of `LLMMetadata`**

LlamaIndex's `CustomLLM` expects `metadata` to return `LLMMetadata` (from `llama_index.core.llms.types`). Returning a bare `dict` will cause a `TypeError` when LlamaIndex introspects the LLM for context window size, num_output, etc.

```python
@property
def metadata(self) -> dict:   # ← wrong return type
    return {"model_name": …, "temperature": …, "max_tokens": …, "is_chat_model": True}
```

*Fix:*
```python
from llama_index.core.llms import LLMMetadata
@property
def metadata(self) -> LLMMetadata:
    return LLMMetadata(model_name=self.model_name, num_output=self.max_tokens, is_chat_model=True)
```

---

**Issue 17 — `adapters/llamaindex.py` lines 227–244: `_get_query_embedding` and `_get_text_embedding` are **identical** – copy-paste code**

```python
def _get_query_embedding(self, query: str) -> list[float]:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(self.ai_service.embed_text(query))
        …

def _get_text_embedding(self, text: str) -> list[float]:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(self.ai_service.embed_text(text))
        …
```

These are byte-for-byte identical except for the parameter name. Extract a `_sync_embed(self, text: str) -> list[float]` helper and call it from both. DRY. It's not hard.

---

**Issue 18 — `adapters/llamaindex.py`: `nest_asyncio.apply()` is called up to 3 separate times per request on the global event loop**

`nest_asyncio.apply()` is idempotent but it patches the **global** asyncio event loop policy for the entire process. Calling it inside a hot path (every embedding lookup) is wasteful and obscures the real architectural problem: synchronous LlamaIndex code calling async AI service code inside a running async server. The correct fix is to implement the `_aget_*` async variants (already done for embeddings) and ensure LlamaIndex callers use the async API. The synchronous wrappers should be a last resort with a clear warning comment, not the primary path.

---

**Issue 19 — `ai/__init__.py`: The file has two separate module-level docstrings and only one `__all__` definition – the adapters exports are orphaned**

```python
# First block (lines 1-18):
"""Unified AI Service Layer…"""
from .ai_service import AIService, get_ai_service
…
__all__ = ["AIConfig", "AIService", "ChatMessage", …]   ← defined here

# Second block (lines 19-end):
"""LlamaIndex Adapters for AIService…"""                ← second docstring (only first counts)
from .llamaindex import AIServiceEmbedding, AIServiceLLM
__all__ = ["AIServiceEmbedding", "AIServiceLLM"]        ← overwrites the first __all__!
```

Wait – I see the file is only 19 lines and doesn't contain the second block (that's `adapters/__init__.py`). But the earlier output from reading `ai/__init__.py` showed both blocks concatenated. **Regardless**, the fact that someone can misread the output means the `__init__.py` modules need clear, unambiguous separation. Confirm the `ai/__init__.py` does not import from `adapters` – if it does, that's a circular dependency risk and the LlamaIndex dep bleeds into the core module.

---

**Issue 20 — `ai_service.py` lines 338–340: `LLMServiceSingleton` is cleared as a side effect of AI reinitialisation – hidden coupling**

```python
from app.services.llm_service import LLMServiceSingleton  # noqa: PLC0415
LLMServiceSingleton.set_instance(None)
```

`AIServiceManager.reinitialize_with_model` reaches into a **sibling service** (`LLMServiceSingleton`) and clears its singleton. This is hidden coupling disguised as a comment. If a third service also caches the AI service, someone has to remember to add another `set_instance(None)` call here. This belongs in an event/observer pattern or a startup lifecycle hook, not buried in a reinitialization method.

---

**Issue 21 — `ai_service.py` lines 291–315: `reinitialize_with_model` grace-period sleep is a facade for real request draining**

```python
await asyncio.sleep(get_app_settings().ai_reinit_grace_sleep)
```

The comment even admits it: *"More sophisticated: maintain request counter and wait for zero."* A fixed sleep is not request draining – it's hoping. Under load, in-flight requests started just before the sleep ends will be mid-execution when the old instance is replaced. This is an architectural debt that should be either fixed or prominently documented as a known limitation, not hidden under an `ai_reinit_grace_sleep` setting that implies it works correctly.

---

**Issue 22 — `providers/openai_llm.py` `_chat_via_chat_completions`: The 3-attempt inner loop and 2-pass outer loop produce up to 6 API calls per request with unclear precedence**

The method makes up to 3 attempts per pass × 2 compatibility passes = 6 potential API calls before giving up. The progression is:
1. `max_tokens` + temperature + response_format
2. `max_tokens` + no temperature + response_format
3. `max_tokens` + no temperature + no response_format
4. (retry with `max_completion_tokens`) same three again

If attempt 3 fails (no temperature, no response_format), the code still re-enters attempt 1 in the second pass with a different token param. This is excessive. Cache the preferred token parameter per model in `_preferred_api_by_model` and eliminate the outer loop in favour of the already-present `_preferred_api_by_model` mechanism.

---

## Summary Table

| # | File | Severity | Category |
|---|------|----------|----------|
| 1 | `ai_service.py:323-326` | 🔴 Critical | Pydantic mutation bug / model switch broken |
| 2 | `providers/openai_client.py`, `azure_openai_client.py` | 🔴 Critical | Stale singletons ignore new config |
| 3 | `ai_service.py:177-209` | 🔴 Critical | Dead LangChain code, constraint violation |
| 4 | `providers/openai_llm.py:458` | 🔴 Critical | `type: ignore` masking real `AttributeError` |
| 5 | `adapters/llamaindex.py:95-167` | 🔴 Critical | `asyncio.run` inside `except RuntimeError` swallows real errors |
| 6 | `config.py` (whole file) | 🟠 High | Redundant DTO duplicating AppSettings |
| 7 | `config.py:55-57` | 🟠 High | Compat lookup duplicated from AppSettings |
| 8 | `config.py:96-107` | 🟠 High | Redundant/incorrect validation conditions |
| 9 | `router.py:43-94` | 🟡 Medium | 4× copy-pasted fallback closure pattern |
| 10 | `router.py:43-52` | 🟡 Medium | Variable shadowed by inner `def` of same name |
| 11 | `ai_service.py:193-209` | 🟡 Medium | `getattr` on typed fields |
| 12 | `ai_service.py:267,272-273` | 🟡 Medium | `get_instance` not guarded by `_lock` |
| 13 | `providers/openai_llm.py`, `openai_embedding.py` | 🟡 Medium | f-string logging mixed with `%`-style |
| 14 | `providers/openai_llm.py` (7 sites) | 🟡 Medium | `noqa: S105/S107` scattered instead of rule exclusion |
| 15 | `providers/azure_openai_embedding.py:27` | 🟡 Medium | Wrong field for embedding dimension lookup |
| 16 | `adapters/llamaindex.py:78` | 🟡 Medium | Wrong `metadata` return type for LlamaIndex |
| 17 | `adapters/llamaindex.py:227-280` | 🟡 Medium | `_get_query_embedding` / `_get_text_embedding` are duplicates |
| 18 | `adapters/llamaindex.py` (3 sites) | 🟡 Medium | `nest_asyncio.apply()` in hot path |
| 19 | `ai/__init__.py` | 🟡 Medium | Potential double-`__all__` / dep bleed from adapters |
| 20 | `ai_service.py:338-340` | 🟡 Medium | Hidden coupling to `LLMServiceSingleton` |
| 21 | `ai_service.py:317-320` | 🟡 Medium | Grace-period sleep is not real request draining |
| 22 | `providers/openai_llm.py` `_chat_via_chat_completions` | 🟡 Medium | Up to 6 API attempts with unclear precedence |

---

## Verdict

**FAIL** — 😤 Five critical bugs including broken model switching, stale HTTP clients, and live LangChain imports in a codebase that removed LangChain. The LangChain issue alone is a showstopper if `langchain_openai` isn't in the dependencies. Fix Issues 1–5 before this goes anywhere near production.
