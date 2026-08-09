# ⚖️ AirJudge — Attribution-Bound Eligibility Adjudication

**Contract (GenVM StudioNet):** `0xfd88Ffe790f90c361BB5bdEBC1A483a3d37699F5`
**Explorer:** https://explorer-studio.genlayer.com/address/0xfd88Ffe790f90c361BB5bdEBC1A483a3d37699F5

An intelligent contract that decides airdrop and reward eligibility from **qualitative** criteria written in plain language, and proves the applicant actually authored the work before approving them.

Deterministic rules handle "wallet has ≥ N transactions" well. They cannot handle "created a meaningful educational contribution" — that judgement normally falls to a centralised reviewer. AirJudge moves it to GenLayer's validator consensus, with the authorship question resolved on-chain rather than assumed.

---

## The Problem This Solves

An AI adjudicator that only reads evidence and scores its quality is trivially farmable:

> Alice writes an excellent tutorial. Bob submits Alice's URL from his own wallet.
> The evidence is genuinely good, so the model approves it. Bob collects the reward.
> Bob repeats this from a hundred wallets.

Judging content quality is the easy half. Binding that content to the claimant is the half that actually protects the campaign.

---

## How It Works

```
register_handle("someoneelse")          → wallet ↔ public handle, set once, immutable
create_campaign(id, name, criteria)     → criteria in natural language
submit_application(id, claim, url)      → requires a registered handle
                                        → evidence URL burned for this campaign
judge_application(id, applicant)
        ↓
  each validator independently:
    CHECK 1  is the visible author on the page the registered handle?
    CHECK 2  does the evidence itself satisfy the campaign criteria?
        ↓
  {"authorship_proven": bool, "verdict": "...", "reason": "..."}
        ↓
  contract re-applies check 1 itself:
    authorship_proven == false  →  NOT_ELIGIBLE, no matter what the model said
        ↓
  ELIGIBLE / NOT_ELIGIBLE written to state
```

---

## Security Model

| Property | Implementation |
|---|---|
| **Attribution** | `register_handle` binds a wallet to a public handle, once, permanently. Validators must locate the author shown on the evidence page and match it against that handle. |
| **Contract-Side Enforcement** | The verdict is not taken on trust. If `authorship_proven` is false, the contract forces `NOT_ELIGIBLE` regardless of the model's own verdict field — a compromised or confused model cannot approve an unattributed submission. |
| **Anti-Replay** | Each evidence URL is burned per campaign at submission time. A second wallet cannot reuse the first wallet's evidence. The same work may still be entered into a different campaign, which is legitimate. |
| **One Application Per Wallet** | Keyed on `campaign_id:applicant`, so a wallet cannot resubmit after a verdict. |
| **Untrusted Claim** | The applicant's own description is fenced in `<CLAIM>` and explicitly marked as proving nothing. Only the evidence counts. |
| **Prompt Injection Fencing** | Evidence is fenced in `<EVIDENCE>`, fence tags are stripped from the content first, and the model is instructed to ignore embedded instructions. |
| **Fail-Closed** | `gl.nondet.web.render` is wrapped so a dead link yields `FETCH_FAILED_*` and a `NOT_ELIGIBLE` verdict, rather than reverting the transaction. |
| **Campaign Lifecycle** | Both `submit_application` and `judge_application` require an active campaign; only the creator can close one. |
| **Idempotent Judging** | An application can only be judged while `PENDING`. |

---

## Contract Methods

| Method | Who | Description |
|---|---|---|
| `register_handle(web2_handle)` | Anyone | Bind a public handle to the wallet. Set once. |
| `create_campaign(campaign_id, name, criteria)` | Anyone | Open a campaign with natural-language criteria |
| `set_campaign_active(campaign_id, active)` | Creator | Open or close the campaign |
| `submit_application(campaign_id, description, evidence_url)` | Registered wallet | Apply with a claim and one public evidence URL |
| `judge_application(campaign_id, applicant)` | Anyone | Run validator adjudication |
| `get_handle(address)` | Anyone | Registered handle for a wallet |
| `is_evidence_used(campaign_id, evidence_url)` | Anyone | Whether a URL is already burned |
| `get_application_status(campaign_id, applicant)` | Anyone | `PENDING` / `ELIGIBLE` / `NOT_ELIGIBLE` |
| `get_application_reason(campaign_id, applicant)` | Anyone | Consensus reasoning |
| `get_application_description(campaign_id, applicant)` | Anyone | The submitted claim |
| `get_application_evidence(campaign_id, applicant)` | Anyone | The submitted evidence URL |
| `get_campaign_name` / `get_campaign_criteria` / `get_campaign_creator` / `is_campaign_active` | Anyone | Campaign details |

---

## On-Chain Test Results (StudioNet)

Campaign `genlayer-edu`, criteria: *"Applicant must have created original educational content explaining GenLayer intelligent contracts."*

| # | Test | Result |
|---|---|---|
| 1 | `register_handle` twice from one wallet | Reverted — `handle already registered for this wallet` |
| 2 | Second wallet submits the first wallet's evidence URL | Reverted — `this evidence URL has already been submitted to this campaign` |
| 3 | Adjudicate evidence authored by someone else | `NOT_ELIGIBLE` |
| 4 | Adjudicate evidence authored by the registered handle | `ELIGIBLE` |

Tests 3 and 4 ran against the **same campaign and the same criteria**. The only variable was whether the evidence was authored by the applicant.

**Test 3** — wallet registered as `nikvn89`, evidence page authored by `@alice`:

> Visible author is @alice, which does not match registered handle nikvn89; authorship not proven.

Equivalence principle output: `{"authorship_proven": false, "verdict": "NOT_ELIGIBLE", ...}` — and the contract's own enforcement would have forced `NOT_ELIGIBLE` even had the model returned otherwise.

**Test 4** — wallet registered as `someoneelse`, evidence page authored by `someoneelse`:

> Authorship proven as 'someoneelse' matches registered handle. Evidence shows original educational content explaining GenLayer intelligent contracts and AI consensus mechanism.

Both adjudications reached accepted consensus across the validator set.

---

## Reproducing the Tests

Deploy the contract, then from wallet A:

```
register_handle("wallet-a-handle")
create_campaign("genlayer-edu", "GenLayer Education Bounty",
                "Applicant must have created original educational content
                 explaining GenLayer intelligent contracts")
submit_application("genlayer-edu", "<claim, 20+ chars>", "<evidence URL>")
```

**Set-once handle** — call `register_handle` again from wallet A. It reverts.

**Anti-replay** — from wallet B, register a handle, then submit wallet A's evidence URL to the same campaign. It reverts.

**Attribution failure** — `judge_application("genlayer-edu", <wallet A>)` where the evidence page names a different author. The status becomes `NOT_ELIGIBLE` and the reason names both handles.

**Happy path** — from wallet B, submit a fresh evidence URL whose page names wallet B's registered handle and whose content satisfies the criteria. Adjudicate it. The status becomes `ELIGIBLE`.

> **Note on evidence URLs:** `gl.nondet.web.render` cannot crawl `raw.githubusercontent.com` or `github.com/.../blob/...`. Use a repository homepage (`github.com/owner/repo`) or a paste host.

---

## Tech Stack

- **Intelligent Contract:** Python on GenVM v0.2.16
- **Adjudication:** `gl.eq_principle.prompt_non_comparative` — validators fetch and evaluate independently
- **Web Access:** `gl.nondet.web.render`
- **Storage:** `TreeMap` for the identity registry, campaigns, applications, and the evidence ledger

---

## Note on Submissions

This repository is the **Intelligent Contract** submission — the adjudication primitive on its own. The full dApp built around it is submitted separately as a Project.
