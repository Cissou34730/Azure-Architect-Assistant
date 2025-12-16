Below is what the **MCP technical service** should do, in detail, without code, and with explicit files, parameters, tools and tests.

We stay strictly inside:

```text
app/services/mcp/
```

and its related config + tests.

---

## 1. Goal and responsibilities of the MCP service

The MCP service must provide a **single, clean abstraction** for all interactions with MCP servers.

Concretely, it must:

1. Hide the **Model Context Protocol** implementation details (Python client, config files, connection lifecycle).
2. Offer a **small, stable interface** to the rest of your code:

   * low-level: “call MCP service X, action Y, with params Z”.
   * higher-level: domain helpers (e.g. “get environment status”, “list deployments”, etc.).
3. Handle:

   * configuration (where are MCP servers defined, how to connect),
   * error mapping (network errors, capability errors, invalid params),
   * observability (logging calls, durations, failures).

The rest of the system (agents, tools, backend) must **never talk to MCP directly**; they only use this service.

---

## 2. Tooling choice (be explicit)

For now, be **prescriptive**:

* Use the **official Python MCP client** as the primary way to talk to MCP servers.
* Do **not** introduce an HTTP gateway at this stage.
* Configuration is done via:

  * an MCP config file (e.g. JSON/YAML) referenced by `MCP_CONFIG_PATH` in `agents_system/config/settings.py`.

If later you need an HTTP proxy, you will **extend** the MCP service implementation but keep the **same public interface** (`MCPClient.call(...)`, `operations.*`).

---

## 3. Files involved for MCP service

You will work (in this step) on these files:

```text
app/
  services/
    mcp/
      __init__.py           # expose public API of the service
      client.py             # MCPClient abstraction (core of this step)
      operations.py         # domain-level helpers built on MCPClient

agents_system/
  config/
    settings.py             # already contains MCP_CONFIG_PATH (ensure it’s wired)

tests/
  services/
    mcp/
      test_client.py        # unit tests of MCPClient
      test_operations.py    # tests of domain helpers
```

We only **describe** what goes where, no code yet.

---

## 4. The low-level MCP client (`client.py`)

### 4.1. Responsibilities

`MCPClient` is the **only place** where:

* MCP config file is read / parsed.
* MCP Python client objects are instantiated.
* any network / RPC / session logic is handled.
* raw responses from MCP servers are normalized to Python structures (`dict`, `list`, etc.).

It must provide:

* A constructor:

  * uses `MCP_CONFIG_PATH` from `settings`.
  * initializes MCP endpoints and capabilities once (lazy or eager, but centralised).
* A single core method:

  ```text
  call(service: str, action: str, params: dict) -> dict
  ```

with the following behavior:

1. Validate inputs:

   * `service` is a known MCP service name.
   * `action` is a valid action for that service (if you have metadata).
2. Send the call to the proper MCP endpoint.
3. Handle:

   * connection errors,
   * timeouts,
   * protocol errors,
   * unsupported capabilities.
4. Normalize the response:

   * always return a JSON-like `dict` (or raise a controlled exception).

### 4.2. Configuration and parameters

* `MCP_CONFIG_PATH` (string): path to MCP config file.
* Optional: per-call timeouts (e.g. default 5–30 seconds).
* Optional: per-service default parameters (retry count, etc.).

The client itself must **not depend** on LangChain or any agent logic.

### 4.3. Error handling and exceptions

Define a small set of custom exceptions in `client.py`, for example:

* `MCPConnectionError`
* `MCPTimeoutError`
* `MCPProtocolError`
* `MCPCapabilityError`
* `MCPUnexpectedResponseError`

`call()` maps low-level exceptions from the MCP library into these.

This is important so higher layers (operations, tools, agents) can:

* decide what to show to the user,
* distinguish “bad input” vs “system unavailable”.

### 4.4. Synchronous vs asynchronous

For this stage:

* Keep the MCP client **synchronous**:

  * `call(...) -> dict` (blocking).
* This aligns with:

  * LangChain Tools default behavior (sync `func`),
  * your other service layers (RAG queries are also sync).

If later you want async, you can add `async_call(...)` or wrap the sync calls.

---

## 5. Domain-level operations (`operations.py`)

`operations.py` focuses on **“what we want MCP to do for us”**, not how.

It builds a set of functions on top of `MCPClient.call()`, each representing a **business-relevant operation**.

### 5.1. Responsibilities

* Translate domain language into MCP calls:

  * Example: `get_environment_status(env: str)` calls MCP service `env_service`, action `get_status`, with params `{ "env": env }`.
* Normalize and simplify responses:

  * Convert raw MCP responses into structures that make sense to your domain (dicts with well-defined keys).
* Encapsulate service/action naming:

  * The rest of the code should **never** hardcode MCP service names or actions.

### 5.2. API shape

Each function should:

* Have a **clear, typed signature**:

  * `get_environment_status(env: str) -> dict`
  * `list_deployments(project_id: str) -> list[dict]`
  * etc.
* Internally:

  * instantiate or receive an `MCPClient`.
  * call `client.call(service, action, params)`.
  * validate and transform the returned dict.

### 5.3. No LLM, no LangChain here

`operations.py` must remain a **pure business service layer**:

* no mention of agents,
* no mention of LangChain tools,
* no knowledge of conversation or checklists.

LangChain tooling (tools, agents) will live under `agents_system/tools/` and `agents_system/agents/`.

---

## 6. Public API (`__init__.py` in `services/mcp`)

In `app/services/mcp/__init__.py` you define what the rest of the project is allowed to import:

* `MCPClient` (if someone wants low-level control).
* `operations.*` functions (preferred usage for most code).

For example, the LangChain tool wrapper in `agents_system/tools/mcp_tool.py` will **only** import from `services.mcp.operations`, not from `client.py` directly.

---

## 7. Configuration wiring (settings)

Ensure `agents_system/config/settings.py` already contains:

* `MCP_CONFIG_PATH: str | None = None`

This is how `MCPClient` finds its configuration.

You might also decide:

* Where the config file lives, e.g.:
  `config/mcp/clients.json` or `.yaml`.
* What it contains:

  * list of MCP servers,
  * mapping of logical service names → endpoints.

Design this file so it’s:

* version-controlled,
* environment-specific if needed (dev/prod paths).

---

## 8. Testing strategy for MCP service

You need **two layers** of tests:

### 8.1. `test_client.py` (MCPClient)

Focus on:

* Initialization:

  * correct behavior if `MCP_CONFIG_PATH` is missing, invalid, or points to a malformed file.
* Normal calls:

  * with a fake or stub MCP backend (or mocking the MCP Python client).
* Error mapping:

  * connection error → `MCPConnectionError`.
  * timeout → `MCPTimeoutError`.
  * invalid response structure → `MCPUnexpectedResponseError`.

You want these tests to verify the **contract**:

* `call()` always returns a dict (on success).
* Exceptions are of the **custom** types defined in `client.py`.

### 8.2. `test_operations.py` (domain helpers)

Focus on:

* That each operation:

  * calls `MCPClient.call()` with the expected `service`, `action`, and `params`.
  * correctly interprets the returned dict.
  * raises meaningful errors if the response doesn’t match expectations (missing keys, wrong types).
* Use mocks/fakes for `MCPClient.call()`; do **not** hit a real MCP server in unit tests.

Optionally later:

* add integration tests against a real MCP dev server, but that’s outside this step.

---

## 9. Non-functional requirements for MCP service

The MCP service should also define:

* **Time-out policy**:

  * default timeout per call,
  * optional override per operation (if needed).
* **Logging**:

  * at least log:

    * `service`, `action`, and maybe a hash of `params` (not sensitive values),
    * start/end timestamps,
    * success/failure and error type.
* **Security**:

  * ensure `MCP_CONFIG_PATH` is controlled by environment, not user input.
  * avoid logging secrets or full payloads when they contain sensitive data.

---
