# Scoring methodology

## Objective

TAFGS measures the strength and materiality of company-level fundamental growth attributable to AI-factory demand. It does not include valuation and therefore does not estimate expected stock return.

## Exposure-aware growth conversion

Let:

- `R0` be current total company revenue.
- `e` be current AI-factory revenue exposure, between 0 and 1.
- `g` be the three-year CAGR of the AI-exposed revenue.
- Non-AI revenue remain flat solely for isolating the AI contribution.

```text
AI revenue now       = R0 × e
AI revenue in year 3 = R0 × e × (1 + g)^3

Company AI-driven CAGR = ((1 - e) + e × (1 + g)^3)^(1/3) - 1
```

This prevents a company with 5% exposure from being treated like a company with 80% exposure to the same end-market growth.

## Operating-margin score

| Reported operating margin | Score |
|---|---:|
| Greater than 40% | 5 |
| 30% through 40%, inclusive | 4 |
| 20% through less than 30% | 3 |
| 10% through less than 20% | 2 |
| Less than 10% | 1 |

Use GAAP/IFRS operating income divided by revenue. Adjusted measures must be stored separately. Segment margin may be used only when the exposure forecast is also segment-specific and the choice is disclosed.

## Moat score

Each component is independently scored 0–5 and combined using the versioned policy:

| Component | Weight |
|---|---:|
| Architectural lock-in | 22% |
| Switching costs | 18% |
| Standards and IP | 18% |
| Ecosystem and design wins | 18% |
| Bottleneck scarcity | 14% |
| Competitive defensibility | 10% |

Anchors:

- `0`: absent or contrary evidence.
- `1`: weak, commodity position.
- `3`: differentiated but replicable position.
- `5`: unusually durable, difficult-to-substitute position supported by primary evidence.

## Risk discount

Risk is severity, not probability-adjusted growth. Each component is scored 0–5, where 5 is most severe:

| Risk | Weight |
|---|---:|
| Customer concentration | 20% |
| Cyclicality | 15% |
| Execution | 20% |
| Supply chain | 15% |
| Geopolitical/regulatory | 15% |
| Commoditization | 15% |

```text
Risk discount = weighted severity / 5 × maximum discount
Maximum discount = 35%
```

The maximum and weights are policy parameters, not agent discretion.

## Final score

```text
Base TAFGS = Moat × Margin Score × Company AI-driven CAGR (%)
Risk-adjusted TAFGS = Base TAFGS × (1 - Risk Discount)
```

Bear, base, and bull scores are calculated independently. Base score determines ordered rank; bear and bull ranks provide a stability range.

Evidence confidence is reported separately. It affects eligibility and rank confidence, not business-quality inputs.

## Capital-stack weights

The supplied reference image implies these seed proportions from $68.445B of displayed amounts:

| Layer | Seed share |
|---|---:|
| Compute/servers | 71.225% |
| Networking | 12.251% |
| Power | 9.686% |
| Cooling | 3.134% |
| Engineering/construction | 3.703% |

These guide market mapping and candidate discovery. They are not multiplied directly into TAFGS because the growth forecast already reflects end-market opportunity. Direct multiplication would double-count capital allocation.

## Rankability gates

A company is excluded when:

- Public-security identity is incomplete.
- Required financial claims lack Tier 1 support.
- Exposure or scenario evidence is missing.
- A moat or risk component is missing.
- Source conflict remains unresolved.
- Evidence confidence is below 65%.
- Citation coverage is below 85%.
- A numeric value is non-finite or outside its permitted range.

