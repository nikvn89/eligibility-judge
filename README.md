# ⚖️ AirJudge — Attribution-Bound Eligibility Adjudication

**Contract (GenVM StudioNet):** `0xE1e34095205Dd31c98DBbb6eeeD1dBbfBC752D80`
**Explorer:** https://explorer-studio.genlayer.com/address/0xE1e34095205Dd31c98DBbb6eeeD1dBbfBC752D80
**Version:** `v0.2.17`

An intelligent contract that decides airdrop and reward eligibility from
**qualitative** criteria written in plain language, and proves the applicant
actually authored the work before approving them.

Deterministic rules handle "wallet has ≥ N transactions" well. They cannot
handle "created a meaningful educational contribution" — that judgement normally
falls to a centralised reviewer. AirJudge moves it to GenLayer's validator
consensus, while keeping the parts that *can* be deterministic — who owns the
evidence, budgets, uniqueness — in the contract, off the model.

---

## The Problem This Solves

An AI adjudicator that only reads evidence and scores its quality is trivially
farmable:

> Alice writes an excellent tutorial. Bob submits Alice's URL from his own
> wallet. The evidence is genuinely good, so the model approves it. Bob collects
> the reward, and repeats from a hundred wallets.

Judging content quality is the easy half. **Binding that content to the
claimant** is the half that actually protects the campaign, and it is the half a
thin "LLM decides" wrapper gets wrong.

AirJudge closes two distinct attribution gaps, both **deterministically in the
contract**, before any model is consulted:

1. **Whose account is this?** — `register_handle` proves wallet ↔ handle control
   by reading the address off the handle's own canonical profile page, a URL the
   *contract* derives, not the caller.
2. **Is the evidence actually theirs?** — `submit_application` requires the
   evidence URL to live inside the namespace of the account the wallet proved
   control of, on the provider it proved it on. `github.com/torvalds/linux`
   submitted by a wallet registered as `github:nikvn89` is rejected by string
   comparison, with no LLM involved.

The model is used only for the genuinely subjective question — *does this
evidence satisfy the qualitative criteria* — as a second layer on top of a
deterministic gate, never as the sole decision-maker.

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
        ↓
submit_application(id, claim, url)
  DETERMINISTIC, before any AI:
    · caller holds a verified handle
    · url is well-formed and safe (no @, .., %, backslash)
    · url is inside the caller's own namespace, e.g.
      https://github.com/myhandle/...      ← else revert
    · url not already burned for this campaign (canonicalised)
        ↓
judge_application(id, applicant)
  DETERMINISTIC gate, re-asserted:
    · evidence still inside the registered namespace  ← else NOT_ELIGIBLE
  THEN validator consensus:
    CHECK 1  page still owned by the registered handle on the registered provider
    CHECK 2  does the evidence satisfy the campaign criteria?
        ↓
  {"authorship_proven": bool, "verdict": "...", "reason": "..."}
        ↓
  contract re-applies check 1 itself:
    authorship_proven == false  →  NOT_ELIGIBLE, regardless of the model
        ↓
  ELIGIBLE / NOT_ELIGIBLE written to state
```

---

## What changed in v0.2.17

A steward review found that adjudication used only the bare handle and ignored
the verified provider, so controlling a handle on one site could be treated as
authorship of unrelated content bearing the same handle elsewhere. This version
closes it at the contract layer.

| Change | Effect |
|---|---|
| `submit_application` reads `provider_of`, not just `handle_of`, and binds evidence to `(provider, handle)` | Evidence must live under the exact account, on the exact provider, the wallet proved control of |
| `_require_evidence_owned_by` — deterministic prefix check | `github.com/otheruser/...` and `medium.com/@handle/...` rejected by string comparison, no LLM |
| `_assert_safe_url` | Rejects `@`, `..`, `%`, backslash, whitespace so the prefix test cannot be spoofed |
| Gate re-asserted in `judge_application` | Applications stored before the rule resolve to `NOT_ELIGIBLE`, never left `PENDING` |
| Evidence anti-replay keys canonicalised | `/repo`, `/repo/`, `/repo?x=1` are one key; the per-campaign burn can no longer be bypassed with a trailing character |
| New views `get_allowed_evidence_prefixes`, `is_evidence_url_acceptable` | The binding can be inspected on-chain without sending a transaction |

The model check is now **defence-in-depth** (catching a repo transferred or
forked away from the account), not the primary attribution control.

---

## Security Model

| Property | Implementation |
|---|---|
| **Verifiable Proof of Control** | `register_handle` requires the caller's wallet address to appear on the **canonical profile page** — a URL the contract derives itself from the handle. The caller cannot redirect verification to a page they control. |
| **Evidence Namespace Binding** | Evidence must be hosted under the exact account the wallet proved control of, on that provider — enforced by string comparison in the contract before any AI call, and re-asserted at judging time. A matching handle on another site cannot be used. |
| **Global Handle Uniqueness** | A reverse index (`wallet_of_handle`) ensures one wallet per handle and one handle per wallet. Both checks run before any AI call. |
| **Safe URL / Handle Charset** | Handles restricted to `[a-z0-9-_]`; evidence URLs reject `@`, `..`, `%`, backslash and whitespace, so neither can smuggle path traversal or userinfo into the namespace check. |
| **Contract-Side Enforcement** | If `authorship_proven` is false, the contract forces `NOT_ELIGIBLE` regardless of the model's own verdict field. |
| **Anti-Replay** | Each evidence URL is burned per campaign, compared in canonical form (query, fragment, trailing slash stripped). |
| **One Application Per Wallet** | Keyed on `campaign_id:applicant`; a wallet cannot resubmit after a verdict. |
| **Untrusted Claim** | The applicant's own description is fenced in `<CLAIM>` and explicitly marked as proving nothing. Only the evidence counts. |
| **Prompt-Injection Fencing** | Evidence is fenced in `<EVIDENCE>`, fence tags stripped from content first, and the model told to ignore embedded instructions. Validator model diversity makes a single-model injection fail equivalence rather than pass — the failure mode is fail-safe. |
| **Fail-Closed** | A dead link yields `FETCH_FAILED_*` and `NOT_ELIGIBLE`, rather than reverting the transaction. |

---

## Contract Methods

| Method | Who | Description |
|---|---|---|
| `register_handle(provider, web2_handle)` | Anyone | Verify and bind a public handle to the wallet. Providers: `github`, `x`. Set once, immutable. |
| `create_campaign(campaign_id, name, criteria)` | Anyone | Open a campaign with natural-language criteria |
| `set_campaign_active(campaign_id, active)` | Creator | Open or close the campaign |
| `submit_application(campaign_id, description, evidence_url)` | Verified wallet | Apply with a claim and one evidence URL inside your own namespace |
| `judge_application(campaign_id, applicant)` | Anyone | Run the deterministic gate + validator adjudication |
| `get_allowed_evidence_prefixes(address)` | Anyone | The URL prefixes this wallet may submit evidence under |
| `is_evidence_url_acceptable(address, url)` | Anyone | Dry-run the deterministic attribution gate |
| `get_handle(address)` / `get_provider(address)` | Anyone | Verified handle / provider for a wallet |
| `get_wallet_of_handle(provider, handle)` | Anyone | Wallet registered to a handle (uniqueness check) |
| `get_expected_profile_url(provider, handle)` | Anyone | The canonical URL validators read — publish your wallet address there before registering |
| `is_evidence_used(campaign_id, evidence_url)` | Anyone | Whether a URL is already burned |
| `get_application_status` / `_reason` / `_description` / `_evidence` | Anyone | Application state |
| `get_campaign_name` / `_criteria` / `_creator` / `is_campaign_active` | Anyone | Campaign details |

---

## Registering a Handle

Before calling `register_handle`, publish your wallet address in the public
profile of the handle you are claiming — the GitHub bio at
`https://github.com/settings/profile`. Call
`get_expected_profile_url("github", "yourhandle")` to see the exact URL
validators will fetch, then:

```
register_handle("github", "yourhandle")
```

Validators fetch `https://github.com/yourhandle` and verify your wallet address
appears on the page. If it does, the handle is permanently bound to your wallet.

---

## On-Chain Test Results (StudioNet, v0.2.17)

Campaign `genlayer-edu`, criteria: *"Applicant must have created original
educational content explaining GenLayer intelligent contracts."* Registered
identity: `github:nikvn89` ↔ `0xE7241B8b44e3f8a0FcCdfF6f4b76380d152F2A61`.

| # | Test | Result | Tx |
|---|---|---|---|
| 1 | Register with wrong wallet in bio | Reverted — `Proof of control failed` | `0x057783…f08bba6` |
| 2 | Register a second handle from same wallet | Reverted — `already has a registered handle` | `0xc4385a…5b1c372f` |
| 3 | Second wallet registers the same handle | Reverted — `already registered by wallet 0xe724…` | `0xd6cb74…89dc939` |
| 4 | **Cross-account evidence** `github.com/torvalds/linux` | Reverted — `must be hosted under the registered account` **(deterministic, no LLM)** | `0x843c12…9eb2b5dd` |
| 5 | Cross-provider evidence `medium.com/@nikvn89/...` | Reverted — `contains a disallowed sequence` | `0xa74248…1fa90e85` |
| 6 | Legitimate submission `github.com/nikvn89/eligibility-judge` | `PENDING` | `0xb922c2…37786e2a30` |
| 7 | Adjudicate owned evidence meeting criteria | `ELIGIBLE`, `authorship_proven: true` | `0xf29bd8…fab728bc` |

Test 4 is the attribution gap from the review: it now fails at the contract
layer, by string comparison, before any model is called.

---

## Reproducing the Tests

Full copy-paste walkthrough in **[TESTING.md](./TESTING.md)**. In short: deploy,
add your wallet address to your GitHub bio, then `register_handle` →
`create_campaign` → `submit_application` (with a URL under
`github.com/<yourhandle>/`) → `judge_application`.

Confirm the gate with a free view call before spending a transaction:

```
is_evidence_url_acceptable("<your wallet>", "https://github.com/torvalds/linux")   → false
is_evidence_url_acceptable("<your wallet>", "https://github.com/<yourhandle>/repo") → true
```

> **Evidence URLs:** `gl.nondet.web.render` reads a repository homepage
> (`github.com/owner/repo`) well. It cannot crawl `raw.githubusercontent.com` or
> `.../blob/...`.

---

## Known Limitations

- **URL charset is conservative.** `_assert_safe_url` rejects `%` and `@`
  anywhere in the URL to keep the prefix test unspoofable; this also rejects
  otherwise-valid GitHub URLs containing percent-encoding (e.g. a filename with
  a space). Use a URL without percent-encoding.
- **Handle reuse.** GitHub and X allow a username to be released and re-claimed
  by another person; the on-chain binding is permanent and does not track that.
- **Repository transfer.** A repo moved to another account after submission is
  caught by the model check, not deterministically.
- **The `x` provider.** Supported in code, but `x.com` serves a login wall to
  anonymous fetches, so both proof-of-control and evidence rendering usually
  fail there. `github` is the working path in this version.

---

## Tech Stack

- **Intelligent Contract:** Python on GenVM, `v0.2.17`
- **Adjudication:** `gl.eq_principle.prompt_non_comparative` — validators fetch
  and evaluate independently
- **Web Access:** `gl.nondet.web.render`
- **Storage:** `TreeMap` for the identity registry (forward + reverse index),
  campaigns, applications, and the evidence ledger

---

## Note on Submissions

This repository is the **Intelligent Contract** submission — the adjudication
primitive on its own. The full dApp built around it is submitted separately as a
Project.
