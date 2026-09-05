# Agents, prompts, and tool permissions

## Why these are separate agents

An agent exists only where the task has a distinct judgment rubric, context boundary, or tool permission. Arithmetic services are not disguised as agents. Agents do not converse freely; they update typed state under the workflow supervisor.

## Agent contracts

| Agent | Owns | Does not own | Tools |
|---|---|---|---|
| Eligibility | Public security and universe eligibility | Investment quality | Security-master lookup |
| Evidence | Completeness, source-tier confidence, conflicts | Numeric estimates | Evidence-ledger query |
| Exposure | Present AI-factory revenue exposure | Final growth or rank | Segment/revenue claim retrieval |
| Moat | Six defensibility components | Margin, forecast, rank | Technical and ecosystem evidence |
| Margin | Reported operating margin and rubric bucket | Adjusted narrative or rank | XBRL/financial calculator |
| Growth | Bear/base/bull driver scenarios | TAFGS calculation | Forecast evidence and scenario calculator |
| Risk | Six severity components | Silent formula changes | Risk evidence and policy lookup |
| Skeptic | Contradictions, citation and quality gates | Thesis advocacy | Read-only access to all approved claims |
| Narrative | Approved investor-readable profile | New facts or numeric changes | Approved dossier; optional model |
| Ranking service | Formula, sorting, rank stability | Qualitative judgment | Deterministic code only |
| Report service | Template and provenance manifest | New research | Approved database records only |

## Common prompt contract

The versioned prompt under `config/prompts/common.txt` enforces:

- Role and decision boundary.
- Point-in-time cutoff.
- Primary-source preference.
- Retrieved-document instructions treated as untrusted data.
- Fact/calculation/assumption separation.
- Evidence ID for each claim.
- Disconfirming-evidence search.
- Strict JSON output and explicit abstention.

Role-specific rubrics are appended from separate prompt files. Prompt versions are stored in every run manifest.

## Model routing

Default `offline` mode uses structured evidence and deterministic templates. Numeric scoring is fully available without an LLM.

Optional modes:

```text
AIFACTORY_MODEL_PROVIDER=ollama
AIFACTORY_MODEL_NAME=your-local-model
AIFACTORY_MODEL_BASE_URL=http://localhost:11434
```

or:

```text
AIFACTORY_MODEL_PROVIDER=openai_compatible
AIFACTORY_MODEL_NAME=approved-model-name
AIFACTORY_MODEL_BASE_URL=https://approved-gateway.example.com
AIFACTORY_MODEL_API_KEY=secret
```

For OpenRouter, use its canonical API base. The free Nemotron Lightning model is
appropriate for high-throughput narrative calls:

```text
AIFACTORY_MODEL_PROVIDER=openai_compatible
AIFACTORY_MODEL_NAME=nvidia/nemotron-3.5-lightning:free
AIFACTORY_MODEL_BASE_URL=https://openrouter.ai/api/v1
AIFACTORY_MODEL_API_KEY=secret
AIFACTORY_MODEL_MAX_COMPLETION_TOKENS=800
AIFACTORY_MODEL_REASONING_EFFORT=none
```

The CLI loads a local `.env` file without overriding environment variables already
set by the runtime. `.env` is gitignored. Verify routing with `aifactory model-check`;
the command reports provider/model status but never prints credentials or model output.
The completion cap and disabled reasoning keep narrative-only calls bounded on the
rate-limited free endpoint; increase them only after measuring batch latency.

Free OpenRouter endpoints may retain prompts according to the selected provider's
data policy. Restrict them to public evidence and synthetic/test records; use a
provider configuration approved by your organization for confidential analyst notes.

Model output is used for narrative enrichment and **review-only evidence proposals**. The extraction path uses a versioned JSON schema, exact-quote verification, configured numeric ranges, confidence caps, and a separate analyst decision. A model proposal never becomes an evidence claim automatically. Financial revenue and operating-margin claims remain deterministic SEC XBRL extractions.

## Context construction

Do not send the complete research lake to every model call. Build a role-specific context:

1. Company/security identity.
2. Research cutoff.
3. Relevant rubric version.
4. Only evidence claims needed by the role.
5. Contrary claims.
6. Explicit output schema.

This reduces cost, prompt-injection surface, and cross-company leakage.

## Tool security

- Retrieval tools are read-only.
- Ranker and reporter have no internet access.
- Model credentials never enter workflow state.
- External source URLs allow HTTPS only and reject private, loopback, link-local, and reserved addresses.
- Local HTTP is permitted only for explicitly configured loopback model endpoints.
- All document instructions remain quoted data.
- Maximum retries, concurrency, and workflow steps are bounded.

## Agent evaluation

Each agent needs a labelled dataset distinct from the model used to generate proposals:

- Exposure: analyst interval overlap and materiality error.
- Moat: component-level agreement and rationale evidence coverage.
- Margin: exact numeric match and accounting-period match.
- Growth: driver coverage, scenario ordering, and walk-forward calibration.
- Risk: category recall and analyst severity agreement.
- Skeptic: unsupported-claim recall without excessive false rejection.
- Narrative: no-new-facts rate and citation correctness.
