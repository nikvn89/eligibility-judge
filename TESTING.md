# Testing

These steps reproduce the core onchain behavior of the Contribution Eligibility Judge on GenLayer Studio.

## Contract

`0x7bf078785CB95Ac52FdcDaCf80b4Cc839e129C22`

## Positive Test

### 1. Create campaign

Call:

`create_campaign`

Example values:

```text
campaign_id:
positive-test-20260809-01

name:
GenLayer Positive Eligibility Test

criteria:
Applicant must provide a public educational resource that meaningfully explains GenLayer, Intelligent Contracts, or how developers can build on GenLayer. The evidence must contain substantive GenLayer-related educational or technical information.
```

### 2. Submit application

Call:

`submit_application`

```text
campaign_id:
positive-test-20260809-01

description:
I provide a public educational resource containing technical information about GenLayer and Intelligent Contracts.

evidence_url:
https://docs.genlayer.com/
```

Before adjudication:

`get_application_status(...) -> PENDING`

### 3. Judge

Call:

`judge_application(campaign_id, applicant)`

Expected final result:

`ELIGIBLE`

Expected stored reason:

`Approved by GenLayer AI consensus`

## Negative Test

### 1. Create campaign

```text
campaign_id:
negative-test-20260809-01

name:
GenLayer Negative Eligibility Test

criteria:
Applicant must provide a public and meaningful educational contribution specifically about GenLayer, Intelligent Contracts, or building on GenLayer. Unrelated content, generic blockchain content, spam, empty pages, or purely promotional content is not eligible.
```

### 2. Submit an unsupported claim

```text
description:
I created an original educational contribution explaining GenLayer and Intelligent Contracts for developers.

evidence_url:
https://www.python.org/
```

Before adjudication:

`get_application_status(...) -> PENDING`

### 3. Judge

Call:

`judge_application(campaign_id, applicant)`

Observed result:

`NOT_ELIGIBLE`

Observed stored reason:

`Rejected by GenLayer AI consensus`

The Studio consensus view showed the transaction as `ACCEPTED / SUCCESS`, with the Equivalence Principle output `NOT_ELIGIBLE`. Multiple validators participated; the final consensus was accepted even though one validator disagreed.

## Notes

- Use a fresh `campaign_id` for every new test.
- Public evidence URLs must begin with `https://`.
- The current MVP accepts one evidence URL per application.
- `gl.nondet.web.render` may not render every website equally well.
- GenLayer Studio has request-rate limits, so avoid repeatedly resubmitting the same transaction.
