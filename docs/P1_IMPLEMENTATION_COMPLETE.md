# P1 Implementation Complete: Advisory Quality Scoring & Behavior Testing

**Status:** ✅ Both P1 tasks completed  
**Date:** 2025-01-22  
**Related:** [REFACTORING_AND_HARDENING_PLAN.md](./REFACTORING_AND_HARDENING_PLAN.md), [P0_IMPLEMENTATION_COMPLETE.md](./P0_IMPLEMENTATION_COMPLETE.md)

## Summary

This document confirms completion of the 2 P1 (priority 1, short-term) tasks from the refactoring plan. These features enable quantitative evaluation of the agent's proactive advisor behavior.

## Completed Tasks

### 1. ✅ Agent Advisory Quality Scoring

**Objective:** Measure agent's proactive advisory behavior across 4 dimensions

**Implementation:**

Added `_evaluate_advisory_quality(answer, request)` function to `aaa_e2e_runner.py` that scores each agent response on a 0-8 scale:

**Scoring Dimensions (0-2 each):**

1. **Proactivity (0-2):** Does the agent propose next steps, suggest improvements, or drive the conversation forward?
   - Indicators: "I recommend", "consider", "shall I", "next step", "missing", "notice you"
   - 2 points: 3+ indicators (strong proactivity)
   - 1 point: 1-2 indicators (some proactivity)
   - 0 points: No indicators (passive response)

2. **Correction (0-2):** Does the agent challenge assumptions or point out issues?
   - Indicators: "however", "but", "risk", "concern", "trade-off", "not recommended", "violation"
   - 2 points: 3+ indicators (strong challenge/correction)
   - 1 point: 1-2 indicators (some correction)
   - 0 points: No indicators

3. **Evidence (0-2):** Does the agent provide citations, sources, or references?
   - Indicators: URLs, "microsoft.com", "according to", "WAF", "documentation", "guidance"
   - 2 points: 5+ references (strong evidence)
   - 1 point: 2-4 references (some evidence)
   - 0 points: 0-1 references (minimal evidence)

4. **Clarity (0-2):** Is the response well-structured and clear?
   - Checks: Headings (## or ###), lists (3+ bullets), sections (3+ paragraphs), length (200+ chars)
   - 2 points: Headings + lists (well-structured)
   - 1 point: Some formatting or adequate length
   - 0 points: Brief or unstructured

**Pass Threshold:** Total score >= 4 out of 8 (average of 50%)

**Integration:**
- Scoring runs automatically for every chat turn in E2E tests
- Each turn gets `advisoryQuality` field in step record
- Report includes aggregate `advisoryQuality` summary with:
  - Average scores per dimension
  - Turn pass rate
  - Overall pass/fail

**Example output in report:**
```json
{
  "advisoryQuality": {
    "averages": {
      "proactivity": 1.6,
      "correction": 1.4,
      "evidence": 1.8,
      "clarity": 1.2,
      "total": 6.0,
      "maxTotal": 8
    },
    "turnsPassed": 4,
    "totalTurns": 5,
    "passRate": 0.8,
    "overallPassed": true
  }
}
```

---

### 2. ✅ Behavior-Focused Test Scenario

**Objective:** Create test scenarios that specifically evaluate agent's "force of proposition" behavior

**Created:** `scenario-behavior` with Payment API brief

**Scenario Design:**

**Project Context:**
- Payment processing API with 10,000 TPS globally
- PCI DSS compliance required
- 7-year data retention
- <500ms response time
- Small team, startup budget

**Test Turns (designed to trigger proactive behavior):**

1. **Turn 1: Suboptimal Technology Choice**
   - User: "Use Azure SQL Database with DTU-based pricing for 10,000 TPS globally"
   - Expected: Agent should challenge DTU vs vCore, question single-DB for global scale, suggest Cosmos DB

2. **Turn 2: Missing Disaster Recovery**
   - User: "Architecture looks good. Let's use single region."
   - Expected: Agent should push back on single-region for 24/7 payment system, propose multi-region, mention RPO/RTO

3. **Turn 3: Vague Security**
   - User: "For security, we'll just use HTTPS and call it a day."
   - Expected: Agent should expand on PCI DSS requirements, mention WAF, identity/access, encryption at rest, key management

4. **Turn 4: No Monitoring**
   - User: "We don't need monitoring for first version."
   - Expected: Agent should strongly challenge this for payment system, mention compliance/audit requirements, propose minimal viable monitoring

5. **Turn 5: Next Steps Proposition**
   - User: "I've made my decisions. That's all for now."
   - Expected: Agent should proactively propose next steps (ADRs, diagrams, validation, IaC), not just say "okay"

**Expected Advisory Quality Scores:**

Each turn should score >= 4/8 if agent behaves proactively:
- Turn 1: High correction (DTU challenge), high proactivity (Cosmos suggestion)
- Turn 2: High correction (DR challenge), high evidence (WAF HA guidance)
- Turn 3: High proactivity (expand security), high evidence (PCI DSS references)
- Turn 4: High correction (monitoring required), high clarity (structured response)
- Turn 5: High proactivity (propose next steps), high clarity (clear roadmap)

**Files Created:**
- `scripts/e2e/scenarios/scenario-behavior/scenario.json`
- `scripts/e2e/scenarios/scenario-behavior/inputs/brief.md`

---

## How to Use

### Running Behavior Test

```powershell
# Run behavior-focused scenario
uv run python scripts\e2e\aaa_e2e_runner.py --scenario scenario-behavior --mode in-process

# Check advisory quality scores in report
$report = Get-Content scripts\e2e\runs\<run-id>\report.json | ConvertFrom-Json
$report.advisoryQuality
```

### Interpreting Results

**Per-Turn Scores:**
```json
{
  "id": "turn1-suboptimal-choice",
  "advisoryQuality": {
    "proactivity": 2,
    "correction": 2,
    "evidence": 1,
    "clarity": 2,
    "total": 7,
    "maxTotal": 8,
    "passed": true,
    "details": {
      "proactivity": "Strong proactivity (4 indicators)",
      "correction": "Strong correction/challenge (5 indicators)",
      "evidence": "Some evidence (3 references)",
      "clarity": "Well-structured (headings + lists)"
    }
  }
}
```

**Aggregate Report:**
- `overallPassed: true` means agent demonstrated proactive behavior across scenario
- `passRate: 0.8` means 80% of turns scored >= 4/8
- Individual dimension averages show strengths/weaknesses

---

## Benefits

### Quantitative Behavior Measurement
- No longer subjective "does it feel proactive?"
- Concrete 0-8 scale per turn
- Trend tracking across agent versions

### Automated Regression Detection
- If proactivity score drops from 1.8 → 0.5, prompt or tool change broke proactive behavior
- Golden comparison can catch advisory quality regressions

### Focused Improvement
- Low correction scores → strengthen challenge/pushback in prompt
- Low evidence scores → improve KB/MCP tool usage
- Low clarity scores → add formatting instructions

### Real-World Test Cases
- `scenario-behavior` captures actual anti-patterns:
  - Users picking suboptimal tech
  - Missing critical requirements (DR, monitoring)
  - Vague statements needing expansion
  - Expecting agent to drive next steps

---

## Next Steps

### Immediate Testing

1. **Run behavior scenario:**
   ```powershell
   uv run python scripts\e2e\aaa_e2e_runner.py --scenario scenario-behavior --mode in-process
   ```

2. **Review scores:**
   - Check if agent scores >= 4/8 on challenging turns (1, 2, 4)
   - Check if turn 5 shows proactivity (proposes next steps)

3. **Iterate on prompt:**
   - If scores low, strengthen proactive instructions in `agent_prompts.yaml`
   - Re-run scenario to measure improvement

### P2 Tasks (Nice-to-Have)

4. **Create more behavior scenarios:**
   - Scenario: User contradicts previous decisions (test consistency)
   - Scenario: User provides incomplete requirements (test questioning)
   - Scenario: User asks generic question (test contextualization)

5. **Enhance scoring:**
   - Add "consistency" dimension (contradictions detection)
   - Add "contextualization" dimension (ties to project state)
   - Weight dimensions by turn type (validation turns should score high on evidence)

6. **Golden thresholds:**
   - Define acceptable advisory quality ranges per scenario type
   - Fail CI if scores drop below threshold

---

## Acceptance Criteria (All Met ✅)

- [x] `_evaluate_advisory_quality()` function implemented with 4 dimensions
- [x] Scoring integrated into every E2E turn
- [x] Aggregate metrics in report (averages, pass rate, overall pass/fail)
- [x] `scenario-behavior` created with 5 challenging turns
- [x] Brief includes global scale, compliance, high throughput (forces proactive advice)
- [x] Documentation complete with usage examples

---

## Risk Mitigation

### Risk: Scoring too sensitive to wording
**Mitigation:** Indicator lists are broad (15+ per dimension). Small wording changes won't dramatically shift scores. Monitor false negatives in future scenarios.

### Risk: Agent passes score but feels passive
**Mitigation:** Combine advisory quality score with manual review of behavior scenario responses. If score is high but behavior feels wrong, refine indicators.

### Risk: Behavior scenario too specific
**Mitigation:** Scenario-behavior tests general patterns (challenge bad choices, propose next steps). Not tied to specific tech. Can reuse pattern for other domains.

---

## Conclusion

P1 tasks complete. Agent advisory behavior is now measurable and testable. The `scenario-behavior` test case provides a realistic challenge that requires:

- Challenging user's suboptimal choices ✓
- Correcting missing critical requirements ✓
- Expanding vague statements ✓
- Proposing next steps autonomously ✓

Run the behavior scenario to validate P0 + P1 changes together. If agent scores >= 4/8 average, it's behaving as a "force of proposition" as intended.

**Next action:** `uv run python scripts\e2e\aaa_e2e_runner.py --scenario scenario-behavior --mode in-process`
