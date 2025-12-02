Below is a **clean, developer-ready, AI-ready specification** written in English and formatted in Markdown.
It is structured so that an AI development agent can directly start implementing the architecture.

---

# **Azure Architect Assistant – Technical Specification (v1)**

*Architecture: ReAct Core + Atomic Rules + Dynamic Checklists + Decision Log*

---

# **1. Overview**

The Azure Architect Assistant is an AI-driven system designed to support Cloud Solution Architects during discovery, design, and validation phases.
The assistant uses:

* **ReAct-style reasoning** for orchestrating tool calls
* **Atomic Rules stored in a vector database** for deterministic architectural compliance
* **Dynamic Checklist Injection** for guided questioning
* **A Decision Log** as the source of truth for project state
* **Human arbitration** for final decisions and conflict resolution

This specification provides all required components for implementation.

---

# **2. High-Level Architecture**

```
User ↔ LLM (ReAct) ↔ Tool Layer
                   ↳ Topic Detector
                   ↳ Atomic Rules RAG
                   ↳ Decision Log Store
```

* **LLM (ReAct)**: Controls reasoning, calls tools, compares rules vs. decisions, generates questions.
* **Topic Detector**: Determines which domain (SQL, Network, Identity, etc.) is currently being discussed.
* **Atomic Rules RAG**: Retrieves deterministic rules tagged for the relevant domain.
* **Decision Log**: Stores architectural decisions with status (Confirmed / Assumed / Deferred).
* **User**: Always the final arbitrator for conflicts.

---

# **3. System Prompt (LLM Persona)**

> You are the *Azure Architect Assistant*, a ReAct-style agent.
> Your role is to support architectural discovery and design using dynamic checklists generated from Atomic Rules.
> You must:
>
> * Detect the current topic
> * Request relevant rules from the RAG
> * Compare them with the Decision Log
> * Identify missing critical items
> * Ask the user targeted questions
> * Record decisions as Confirmed, Assumed, or Deferred
>   You **never** override the user's decisions.
>   You **never** rely on imagination for rules: all rules come from the RAG.
>   When a conflict or ambiguity arises, you ask the human to arbitrate.

---

# **4. Components Specifications**

## **4.1. Topic Detection Module**

### **Input:**

* Last user message
* Current Decision Log

### **Output:**

* A topic label (string)

  * e.g., `"database"`, `"network"`, `"security"`, `"storage"`, `"identity"`

### **Method:**

* Use embeddings + a lightweight classifier
* If no strong match, fall back to `"general_architecture"`

---

## **4.2. Atomic Rules (RAG Layer)**

Atomic Rules are the deterministic base of the system.

### **Storage Requirements**

* Stored in a vector database (Qdrant, Pinecone, Redis, or similar)
* Ingested from JSON/YAML in Git (Policy-as-Code)

### **Atomic Rule Schema**

```json
{
  "rule_id": "SEC-NET-001",
  "content": "Public exposure is forbidden. Use Private Link.",
  "metadata": {
    "scope_tags": ["SQL", "Storage", "KeyVault", "AKS"],
    "pillar": "Security",
    "criticality": "High",
    "source_version": "WAF-v2.1"
  }
}
```

### **Query Contract**

Input:

```json
{
  "topic": "database"
}
```

Operation:

* Return all rules where `scope_tags` contains `"SQL"` or `"Database"`
* Optionally return transversal rules tagged `"General"` or `"Security"`

Output: list of Atomic Rules.

---

## **4.3. Dynamic Checklist Injector**

Builds a temporary checklist based on the retrieved rules.

### **Steps:**

1. Receive topic from Topic Detector
2. Query the RAG for rules
3. Create a temporary checklist:

```json
{
  "topic": "database",
  "rules": [
    { "rule_id": "...", "criticality": "...", "content": "..." }
  ]
}
```

4. Compare checklist vs. Decision Log
5. Identify gaps (critical rules missing, assumptions, conflicts)

### **Output:**

* A list of **missing rule items** requiring user clarification
* A list of rule conflicts (if any)

---

## **4.4. Decision Log**

The Decision Log is the persistent project memory.

### **Schema**

```json
{
  "decisions": [
    {
      "id": "DL-001",
      "rule_id": "SEC-NET-001",
      "content": "The system must use Private Link for all data services.",
      "status": "Confirmed", // Confirmed | Assumed | Deferred
      "source": "user"
    }
  ]
}
```

### **Operations**

#### Add or update:

```json
{
  "action": "update",
  "rule_id": "SEC-NET-001",
  "status": "Assumed",
  "content": "Using Private Link unless constraints appear later."
}
```

#### Query:

* `get_decisions_by_topic(topic)`
* `get_missing_critical_rules(topic)`
* `detect_conflicts()`

---

# **5. Conflict Detection and Human Arbitration**

The LLM is *not* allowed to resolve rule conflicts.

### **Conflict Example**

Rules:

* `PERF-DB-003`: *"Enable read cache for SQL"*
* `SEC-DB-005`: *"Disable cache for sensitive data"*

### **LLM Response Pattern**

> The rule **PERF-DB-003** requires enabling the read cache.
> The rule **SEC-DB-005** requires disabling cache for sensitive data.
> These constraints conflict.
> Please choose one of the following:
>
> * A: Prioritize Security
> * B: Prioritize Performance
> * C: Provide additional context

The user’s choice is then recorded in the Decision Log.

---

# **6. Passing Definition of Done (DoD)**

### **DoD-P (POC Mode)**

A flexible mode:

* All **critical rules** must be either `Confirmed` **or** `Assumed`
* Allows progression even with some assumptions

### **DoD-X (Production Mode)**

Strict:

* All **critical rules** must be `Confirmed`
* No unresolved conflicts
* All cross-cutting rules must be addressed

### **Check Function**

```python
def check_dod(decision_log, rules):
    critical = [r for r in rules if r["criticality"] == "High"]
    decided = [d for d in decision_log if d["status"] in ["Confirmed", "Assumed"]]

    return len(decided) >= len(critical)
```

---

# **7. ReAct Loop Specification**

The LLM should follow this internal reasoning loop:

1. **Thought:**
   “What is the user talking about? What topic is this?”

2. **Action:**

   * `call_topic_detector()`
   * `query_atomic_rules(topic)`
   * `compare_rules_with_decision_log()`

3. **Observation:**

   * List of missing rules
   * Conflicts
   * Previously confirmed decisions

4. **Thought:**
   “Which missing rule is the most critical to resolve next?”

5. **Action:**
   “Ask the user a targeted question.”

6. **Output:**

   * Human-facing question
   * Optional update to the Decision Log

---

# **8. Output Format to the User**

Every LLM response must include:

### **A. Natural Language Output**

* Summary of current understanding
* Targeted question about a missing rule
* Conflict explanation if needed

### **B. Decision Log Update Block (JSON)**

```json
{
  "decision_update": {
    "rule_id": "SEC-NET-001",
    "status": "Assumed",
    "content": "Private Link will be used for all SQL services."
  }
}
```

If no update:

```json
{ "decision_update": null }
```

---

# **9. Minimal Dataset for POC**

Provide ~20 Atomic Rules with tags:

* SQL
* Storage
* Networking
* Identity
* Security (cross-cutting)
* Monitoring (cross-cutting)

At least 5 with `criticality = "High"`.

---

# **10. Non-Functional Requirements**

### **Latency**

* Cache topic-level rules for the whole session
* Avoid full RAG scans
* Only query per-topic

### **Auditability**

* Every question must refer to rule_id when relevant

### **Extensibility**

* Adding a new technology (PostgreSQL, CosmosDB, etc.)
  = just adding rules and tags
  (no code changes)

---

# **11. Deliverables**

* Topic Detection service
* RAG ingestion pipeline (Atomic Rules → embeddings)
* Dynamic Checklist Injector
* Decision Log store + API
* LLM ReAct system prompt
* Orchestrator implementing the ReAct flow
* 20 sample Atomic Rules for POC

---

