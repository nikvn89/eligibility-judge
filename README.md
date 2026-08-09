# Contribution Eligibility Judge

A reusable GenLayer Intelligent Contract primitive for adjudicating whether a public contribution satisfies a campaign's natural-language eligibility criteria.

## Problem

Many reward, grant, community, and token-distribution programs can verify deterministic facts such as transaction count or wallet balance, but they struggle with subjective criteria such as:

- "meaningful educational contribution"
- "original technical work"
- "substantive community contribution"
- "evidence that actually supports the applicant's claim"

These decisions are usually handled by a centralized team or reviewer.

## Solution

Contribution Eligibility Judge lets a campaign creator define eligibility criteria in natural language. Applicants submit a short claim plus a public evidence URL. GenLayer then evaluates the evidence through decentralized AI consensus and stores one of two final verdicts onchain:

- `ELIGIBLE`
- `NOT_ELIGIBLE`

The applicant's own description is treated as an untrusted claim. The public evidence must substantiate it.

## Why GenLayer

This is not a deterministic eligibility checker.

A conventional smart contract can verify rules such as:

- wallet balance >= X
- transactions >= Y
- timestamp < snapshot

It cannot reliably judge whether a contribution is meaningful, original, relevant, or sufficiently supported by unstructured public evidence.

GenLayer is used for the part that requires interpretation and judgment:

`natural-language criteria + public evidence -> decentralized AI adjudication -> onchain verdict`

The contract uses:

- GenLayer web access via `gl.nondet.web.render`
- `gl.eq_principle.prompt_non_comparative`
- validator consensus over the eligibility decision
- persistent onchain state for the final verdict

## Contract Flow

1. Campaign creator calls `create_campaign`.
2. Applicant calls `submit_application`.
3. Application status becomes `PENDING`.
4. Anyone can call `judge_application`.
5. GenLayer renders the public evidence URL.
6. AI validators evaluate the evidence against the campaign criteria.
7. Consensus resolves to `ELIGIBLE` or `NOT_ELIGIBLE`.
8. The final status and consensus reason are stored onchain.

## Public Methods

### Write

- `create_campaign(campaign_id, name, criteria)`
- `set_campaign_active(campaign_id, active)`
- `submit_application(campaign_id, description, evidence_url)`
- `judge_application(campaign_id, applicant)`

### Read

- `get_campaign_name(campaign_id)`
- `get_campaign_criteria(campaign_id)`
- `get_campaign_creator(campaign_id)`
- `is_campaign_active(campaign_id)`
- `get_application_status(campaign_id, applicant)`
- `get_application_description(campaign_id, applicant)`
- `get_application_evidence(campaign_id, applicant)`
- `get_application_reason(campaign_id, applicant)`

## Consensus Design

`judge_application` copies deterministic campaign/application state, renders the submitted public evidence, and invokes `prompt_non_comparative`.

The adjudication task is intentionally narrow:

> Decide whether the applicant satisfies the campaign eligibility criteria based on the public evidence.

The output is constrained to exactly one of:

- `ELIGIBLE`
- `NOT_ELIGIBLE`

Important validator rules encoded in the criteria:

- judge only against the campaign criteria
- treat the applicant description as an untrusted claim
- require public evidence to substantiate the claim
- reject missing, irrelevant, inaccessible, spam, or insufficient evidence

This creates a reusable adjudication primitive rather than a generic LLM wrapper.

## Deployed Contract

GenLayer Studio contract:

`0x7bf078785CB95Ac52FdcDaCf80b4Cc839e129C22`

Network: GenLayer Studio / Studionet

## Verified Onchain Tests

### Positive test

Criteria required a meaningful public educational resource about GenLayer / Intelligent Contracts.

Evidence was relevant GenLayer documentation.

Result:

`ELIGIBLE`

Stored reason:

`Approved by GenLayer AI consensus`

### Negative test

Applicant claimed a GenLayer educational contribution but submitted unrelated evidence from `python.org`.

Result:

`NOT_ELIGIBLE`

Stored reason:

`Rejected by GenLayer AI consensus`

The negative adjudication reached GenLayer consensus even with one validator disagreeing, demonstrating that the final result was produced by validator consensus rather than a single-model decision.

See [TESTING.md](TESTING.md) for reproduction steps.

## Scope

This repository is the **Intelligent Contract submission**.

It intentionally focuses on one reusable primitive: decentralized contribution eligibility adjudication.

A separate full dApp/project can build campaign management, richer evidence submission, allocation tiers, dashboards, appeals, and token-claim UX on top of this primitive.

## GenLayer Version

```text
# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
```

## Repository Structure

```text
contribution-eligibility-judge/
├── contracts/
│   └── airjudge.py
├── README.md
├── TESTING.md
└── LICENSE
```

## License

MIT
