# Testing AirJudge

Every test below was executed against the live contract on GenLayer StudioNet.

**Contract:** `0xfd88Ffe790f90c361BB5bdEBC1A483a3d37699F5`
**Explorer:** https://explorer-studio.genlayer.com/address/0xfd88Ffe790f90c361BB5bdEBC1A483a3d37699F5

---

## Test Environment

Two wallets are required, referred to below as **Wallet A** and **Wallet B**.

Evidence pages must be reachable by `gl.nondet.web.render`. Note that it cannot crawl `raw.githubusercontent.com` or `github.com/.../blob/...` — use a repository homepage (`github.com/owner/repo`) or a paste host instead. The runs documented here used pastebin.

Adjudication calls invoke the validator set and take roughly one to two minutes to finalize. Setup calls are ordinary transactions and return immediately.

---

## Setup

**1. Register Wallet A's handle**

```
register_handle("nikvn89")
```

**2. Create the campaign** (from Wallet A)

```
create_campaign(
  campaign_id = "genlayer-edu",
  name        = "GenLayer Education Bounty",
  criteria    = "Applicant must have created original educational content
                 explaining GenLayer intelligent contracts"
)
```

**3. Submit Wallet A's application**

```
submit_application(
  campaign_id  = "genlayer-edu",
  description  = "I wrote a tutorial explaining how GenLayer intelligent
                  contracts reach AI consensus",
  evidence_url = "<paste URL whose page is authored by @alice>"
)
```

The evidence page here is deliberately authored by someone other than Wallet A's registered handle. This sets up test 3.

---

## Test 1 — Handle Registration Is Set-Once

An immutable handle is what makes attribution meaningful. If a wallet could rewrite its handle after seeing which evidence it wanted to claim, the attribution check would be worthless.

**Action** — from Wallet A, which already registered `nikvn89`:

```
register_handle("anothername")
```

**Expected** — the transaction reverts:

```
handle already registered for this wallet
```

**Result** — passed. The transaction finalized with an error and the handle was unchanged.

---

## Test 2 — Anti-Replay On Evidence URLs

Without this control, one good article could be submitted from an unlimited number of wallets.

**Action**

```
# from Wallet B
register_handle("someoneelse")

submit_application(
  campaign_id  = "genlayer-edu",
  description  = "Different description but same evidence link as the first applicant",
  evidence_url = "<the exact URL Wallet A already submitted>"
)
```

**Expected** — the transaction reverts:

```
this evidence URL has already been submitted to this campaign
```

**Result** — passed. Wallet B could not reuse Wallet A's evidence.

The lock is scoped per campaign, so the same work may still be entered into a different campaign. That is intentional — one contribution can legitimately qualify for several programmes.

`is_evidence_used(campaign_id, evidence_url)` can be read beforehand to check a URL without spending a transaction.

---

## Test 3 — Adjudication Rejects Unattributed Evidence

**Action**

```
judge_application("genlayer-edu", <Wallet A address>)
```

Wallet A is registered as `nikvn89`; the evidence page names `@alice` as its author.

**Expected** — `NOT_ELIGIBLE`, with the reason naming the mismatch.

**Result** — passed. The equivalence principle output was:

```json
{"authorship_proven": false, "verdict": "NOT_ELIGIBLE", "reason": "..."}
```

And `get_application_reason` returned:

> Visible author is @alice, which does not match registered handle nikvn89; authorship not proven.

Note that the contract does not rely on the model's `verdict` field alone. Because `authorship_proven` came back false, the contract forces `NOT_ELIGIBLE` regardless of what the model reported — a model that returned `{"authorship_proven": false, "verdict": "ELIGIBLE"}` would still be overridden.

---

## Test 4 — Adjudication Approves Attributed Evidence

**Action**

```
# from Wallet B, registered as "someoneelse"
submit_application(
  campaign_id  = "genlayer-edu",
  description  = "I wrote a beginner guide explaining how GenLayer intelligent
                  contracts reach AI consensus",
  evidence_url = "<fresh paste URL, authored by someoneelse,
                   containing an original explainer on GenLayer>"
)

judge_application("genlayer-edu", <Wallet B address>)
```

**Expected** — `ELIGIBLE`, with the reason citing both the authorship match and the criteria.

**Result** — passed. `get_application_status` returned `"ELIGIBLE"` and `get_application_reason` returned:

> Authorship proven as 'someoneelse' matches registered handle. Evidence shows original educational content explaining GenLayer intelligent contracts and AI consensus mechanism.

---

## Why Tests 3 And 4 Matter Together

Both adjudications ran against **the same campaign and the same criteria**. The only variable between them was whether the evidence page was authored by the applicant's registered handle.

| | Test 3 | Test 4 |
|---|---|---|
| Campaign | `genlayer-edu` | `genlayer-edu` |
| Criteria | identical | identical |
| Evidence quality | acceptable | acceptable |
| Author matches handle | no | yes |
| **Verdict** | **NOT_ELIGIBLE** | **ELIGIBLE** |

This isolates attribution as the deciding factor. A contract that only scored content quality would have approved both.

Both runs reached accepted consensus across the validator set, with individual validators evaluating the evidence independently rather than a single model deciding.

---

## Additional Guards Not Covered Above

These are enforced in the contract and can be exercised the same way:

- **One application per wallet per campaign** — a second `submit_application` from the same wallet reverts with `application already exists`.
- **Idempotent judging** — judging an application that is no longer `PENDING` reverts with `application already judged`.
- **Campaign lifecycle** — `submit_application` and `judge_application` both revert with `campaign is closed` once the creator calls `set_campaign_active(id, false)`. Only the creator may close a campaign.
- **Registration required** — `submit_application` from a wallet with no registered handle reverts with `register a public handle before applying`.
- **Fail-closed fetching** — an unreachable evidence URL yields `FETCH_FAILED_NETWORK_ERROR` inside the prompt input, which the criteria map to `NOT_ELIGIBLE`. The transaction does not revert, so a dead link cannot brick an application.

---

## Rate Limits

GenLayer Studio applies limits of roughly 30 requests per minute and 500 per hour. Adjudication calls are the expensive ones; the setup and revert tests are cheap. Plan a full run to use a handful of adjudications rather than looping.
