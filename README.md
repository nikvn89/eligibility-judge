# ⚖️ AirJudge — Attribution-Bound Eligibility Adjudication

**Contract (GenVM StudioNet):** `DEPLOY_ADDRESS_HERE`
**Explorer:** `https://explorer-studio.genlayer.com/address/DEPLOY_ADDRESS_HERE`

An intelligent contract that decides airdrop and reward eligibility from **qualitative** criteria written in plain language, and proves the applicant actually authored the work before approving them.

Deterministic rules handle "wallet has ≥ N transactions" well. They cannot handle "created a meaningful educational contribution" — that judgement normally falls to a centralised reviewer. AirJudge moves it to GenLayer's validator consensus, with the authorship question resolved on-chain rather than assumed.

---

## The Problem This Solves

An AI adjudicator that only reads evidence and scores its quality is trivially farmable:

> Alice writes an excellent tutorial. Bob submits Alice's URL from his own wallet.
> The evidence is genuinely good, so the model approves it. Bob collects the reward.
> Bob repeats this from a hundred wallets.

Judging content quality is the easy half. Binding that content to the claimant is the half that actually protects the campaign.

A naïve attribution check — letting the user declare their own handle — is also bypassable: the caller could point verification at a page they control, containing whatever text they choose. AirJudge closes this by having the **contract**, not the caller, decide which URL is authoritative for a handle.

---

## How It Works

```
register_handle("github", "myhandle")
        ↓
  Contract derives canonical URL: https://github.com/myhandle
  Validators independently fetch that exact page
  Check: does the caller's wallet address appear on it?
  If yes → handle bound to wallet, immutable
        ↓
create_campaign(id, name, criteria)     → criteria in natural language
submit_application(id, claim, url)      → requires a verified handle
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
| **Verifiable Proof of Control** | `register_handle` requires the caller's wallet address to appear on the **canonical profile page** — a URL the contract derives itself from the handle (e.g. `https://github.com/handle`). The caller cannot redirect verification to a page they control. Only the real account owner can publish text there. |
| **Global Handle Uniqueness** | A reverse index (`wallet_of_handle`) ensures each handle can be claimed by at most one wallet, and each wallet can hold at most one handle. Both checks run before any AI call. |
| **Safe Handle Charset** | Handles are restricted to `[a-z0-9-_]`, max 39 chars, no leading/trailing `-`. This prevents path-traversal or query-injection via the handle when building the canonical URL. |
| **Attribution** | `register_handle` binds a wallet to a verified public handle, once, permanently. Validators must locate the author shown on the evidence page and match it against that handle. |
| **Contract-Side Enforcement** | The verdict is not taken on trust. If `authorship_proven` is false, the contract forces `NOT_ELIGIBLE` regardless of the model's own verdict field. |
| **Anti-Replay** | Each evidence URL is burned per campaign at submission time. A second wallet cannot reuse the first wallet's evidence. |
| **One Application Per Wallet** | Keyed on `campaign_id:applicant`, so a wallet cannot resubmit after a verdict. |
| **Untrusted Claim** | The applicant's own description is fenced in `<CLAIM>` and explicitly marked as proving nothing. Only the evidence counts. |
| **Prompt Injection Fencing** | Evidence is fenced in `<EVIDENCE>`, fence tags are stripped from the content first, and the model is instructed to ignore embedded instructions. |
| **Fail-Closed** | `gl.nondet.web.render` is wrapped so a dead link yields `FETCH_FAILED_*` and a `NOT_ELIGIBLE` verdict, rather than reverting the transaction. |
| **Campaign Lifecycle** | Both `submit_application` and `judge_application` require an active campaign; only the creator can close one. |
| **Verify-Before-Write** | State is committed only after the validator proof succeeds. No rollback needed — `raise` reverts automatically. |

---

## Contract Methods

| Method | Who | Description |
|---|---|---|
| `register_handle(provider, web2_handle)` | Anyone | Verify and bind a public handle to the wallet. Providers: `github`, `x`. Set once, immutable. |
| `create_campaign(campaign_id, name, criteria)` | Anyone | Open a campaign with natural-language criteria |
| `set_campaign_active(campaign_id, active)` | Creator | Open or close the campaign |
| `submit_application(campaign_id, description, evidence_url)` | Verified wallet | Apply with a claim and one public evidence URL |
| `judge_application(campaign_id, applicant)` | Anyone | Run validator adjudication |
| `get_handle(address)` | Anyone | Verified handle for a wallet |
| `get_provider(address)` | Anyone | Provider the handle was verified on |
| `get_wallet_of_handle(provider, handle)` | Anyone | Wallet registered to a handle (uniqueness check) |
| `get_expected_profile_url(provider, handle)` | Anyone | The canonical URL validators will read — publish your wallet address there before registering |
| `is_evidence_used(campaign_id, evidence_url)` | Anyone | Whether a URL is already burned |
| `get_application_status(campaign_id, applicant)` | Anyone | `PENDING` / `ELIGIBLE` / `NOT_ELIGIBLE` |
| `get_application_reason(campaign_id, applicant)` | Anyone | Consensus reasoning |
| `get_application_description(campaign_id, applicant)` | Anyone | The submitted claim |
| `get_application_evidence(campaign_id, applicant)` | Anyone | The submitted evidence URL |
| `get_campaign_name` / `get_campaign_criteria` / `get_campaign_creator` / `is_campaign_active` | Anyone | Campaign details |

---

## Registering a Handle

Before calling `register_handle`, publish your wallet address in the public profile of the handle you are claiming:

- **GitHub:** add the address to your bio at `https://github.com/settings/profile`
- **X:** add the address to your bio at `https://x.com/settings/profile`

You can call `get_expected_profile_url(provider, handle)` to see exactly which URL validators will fetch.

Then call:

```
register_handle("github", "yourhandle")
```

Validators fetch `https://github.com/yourhandle` and verify your wallet address appears on the page. If it does, the handle is permanently bound to your wallet.

---

## On-Chain Test Results (StudioNet)

Campaign `genlayer-edu`, criteria: *"Applicant must have created original educational content explaining GenLayer intelligent contracts."*

| # | Test | Result |
|---|---|---|
| 1 | `register_handle` twice from one wallet | Reverted — `this wallet already has a registered handle` |
| 2 | Different wallet tries to register same handle | Reverted — `handle 'X' on github is already registered by wallet 0x...` |
| 3 | Wallet without bio containing its address tries to register | Reverted — `Proof of control failed for https://github.com/X` |
| 4 | Second wallet submits the first wallet's evidence URL | Reverted — `this evidence URL has already been submitted to this campaign` |
| 5 | Adjudicate evidence authored by someone else | `NOT_ELIGIBLE` |
| 6 | Adjudicate evidence authored by the registered handle | `ELIGIBLE` |

Tests 5 and 6 ran against the **same campaign and the same criteria**. The only variable was whether the evidence was authored by the applicant.

---

## Reproducing the Tests

Deploy the contract. Add your wallet address to your GitHub bio at `https://github.com/settings/profile`, then:

```
register_handle("github", "your-github-username")
create_campaign("genlayer-edu", "GenLayer Education Bounty",
                "Applicant must have created original educational content
                 explaining GenLayer intelligent contracts")
submit_application("genlayer-edu", "<claim, 20+ chars>", "<evidence URL>")
judge_application("genlayer-edu", "<your wallet address>")
```

**Set-once handle** — call `register_handle` again from the same wallet. It reverts.

**Uniqueness** — from a different wallet, try `register_handle("github", "your-github-username")`. It reverts with the registered wallet address.

**Proof of control** — from a different wallet, try `register_handle("github", "torvalds")` (or any handle whose bio does not contain your wallet). It reverts.

**Anti-replay** — from wallet B, register a handle, then submit wallet A's evidence URL to the same campaign. It reverts.

**Attribution failure** — `judge_application` where the evidence page names a different author. Status becomes `NOT_ELIGIBLE`.

**Happy path** — submit fresh evidence whose page names the registered handle and satisfies the criteria. Status becomes `ELIGIBLE`.

> **Note on evidence URLs:** `gl.nondet.web.render` cannot crawl `raw.githubusercontent.com` or `github.com/.../blob/...`. Use a repository homepage (`github.com/owner/repo`) or a paste host.

---

## Tech Stack

- **Intelligent Contract:** Python on GenVM v0.2.16
- **Adjudication:** `gl.eq_principle.prompt_non_comparative` — validators fetch and evaluate independently
- **Web Access:** `gl.nondet.web.render`
- **Storage:** `TreeMap` for the identity registry (forward + reverse index), campaigns, applications, and the evidence ledger

---

## Note on Submissions

This repository is the **Intelligent Contract** submission — the adjudication primitive on its own. The full dApp built around it is submitted separately as a Project.
