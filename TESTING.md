# Testing AirJudge v0.2.17 — Deterministic Evidence Attribution

Every test below targets the deployed GenLayer StudioNet contract whose source
matches `contracts/eligibility-judge.py` in this repository.

**Contract:** `0xE1e34095205Dd31c98DBbb6eeeD1dBbfBC752D80`

**Explorer:** https://explorer-studio.genlayer.com/address/0xE1e34095205Dd31c98DBbb6eeeD1dBbfBC752D80

**Source version marker:** line 1 of the deployed source reads `# v0.2.17`

---

## What changed in v0.2.17

Attribution moved out of the model prompt and into the contract.

Previously `judge_application` read `handle_of` but never `provider_of`, and
`submit_application` accepted any `https://` URL. A wallet that proved control
of `github.com/<h>` could therefore submit evidence from any other host where
`<h>` belongs to a different person, or from a different account on the same
host, and rely on the model to spot the mismatch.

On both supported providers the owning account is part of the URL path. v0.2.17
uses that: `_require_evidence_owned_by(provider, handle, url)` requires the
evidence URL to sit inside the namespace of the account the wallet actually
proved control of, on the provider it proved it on. It is a string comparison,
runs before any AI call, and is re-asserted at judging time.

The model check is now defence-in-depth: it confirms the page has not been
transferred, renamed or forked away from the registered account.

---

## Order matters

State is consumed as you go. Run the phases in order.

- A wallet may hold **one** handle, permanently — Phase 1 negatives must run
  before Phase 1 positives are relied upon.
- A wallet may hold **one application per campaign** — every negative submit in
  Phase 3 must run *before* the positive submit in Phase 4, because a successful
  submit consumes the wallet's slot for that campaign.
- Phase 5 needs a **second campaign**, since Wallet A's slot in the first one is
  already spent.

Reverted calls change no state, so the negatives are safe to run in any order
among themselves.

---

## Environment

```text
Wallet A = owner of the GitHub handle under test   (the "honest" applicant)
Wallet B = second wallet, used for negative tests
```

**Prerequisite before anything else:** Wallet A's complete address must be
published in the public GitHub profile of the handle it will claim — the bio of
`https://github.com/<handle>`.

The wallet that deployed the contract does **not** have to be Wallet A. What
matters is that the bio contains the address of whichever wallet calls
`register_handle`. Confirm the exact page validators will read:

```text
get_expected_profile_url("github", "<handle>")
  → https://github.com/<handle>
```

Only the `github` provider is exercised here — see Known Limitations.

---

# Phase 1 — Identity

## T1 — Proof of control succeeds

From **Wallet A**, after publishing Wallet A's address in the GitHub bio:

```text
register_handle("github", "<handle>")
```

Expected: `SUCCESS`

Verify:

```text
get_handle(<Wallet A>)     → "<handle>"
get_provider(<Wallet A>)   → "github"
```

## T2 — Proof of control fails

From **Wallet B**, claim a handle whose profile does not contain Wallet B's
address:

```text
register_handle("github", "torvalds")
```

Expected revert, containing:

```text
Proof of control failed for https://github.com/torvalds
```

## T3 — One handle per wallet

From **Wallet A**, after T1:

```text
register_handle("github", "some-other-handle")
```

Expected revert:

```text
this wallet already has a registered handle: <handle>
```

## T4 — One wallet per handle

From **Wallet B**:

```text
register_handle("github", "<handle>")
```

Expected revert:

```text
handle '<handle>' on github is already registered by wallet <wallet-a>
```

Verify:

```text
get_wallet_of_handle("github", "<handle>")   → <Wallet A>
```

---

# Phase 2 — Namespace binding is inspectable

These two views expose the deterministic control without sending a transaction.
Run them before any submit — they are the cheapest way to confirm the new
behaviour is actually live at this address.

## T5 — Allowed prefixes are derived from the verified identity

```text
get_allowed_evidence_prefixes(<Wallet A>)
```

Expected:

```text
["https://github.com/<handle>/", "https://gist.github.com/<handle>/"]
```

For a wallet with no registered handle, expected `[]`.

## T6 — Dry-run the gate

```text
is_evidence_url_acceptable(<Wallet A>, "https://github.com/<handle>/eligibility-judge")
  → true

is_evidence_url_acceptable(<Wallet A>, "https://github.com/torvalds/linux")
  → false

is_evidence_url_acceptable(<Wallet A>, "https://medium.com/@<handle>/anything")
  → false

is_evidence_url_acceptable(<Wallet A>, "https://github.com/<handle>")
  → false      (profile page is not evidence for itself)
```

---

# Phase 3 — Campaign and negative submits

## T7 — Create campaign

From any wallet:

```text
create_campaign(
  "genlayer-edu",
  "GenLayer Education Bounty",
  "Applicant must have created original educational content explaining GenLayer intelligent contracts."
)
```

## T8 — Registration required before applying

From an **unregistered wallet**:

```text
submit_application(
  "genlayer-edu",
  "I created a substantive public contribution explaining GenLayer.",
  "https://github.com/anyone/anything"
)
```

Expected revert:

```text
register and verify a public handle before applying
```

This fires before the namespace check, so it is unaffected by v0.2.17.

## T9 — ★ Cross-account, same provider

**This is the attack the steward reported. It now fails with no model involvement.**

From **Wallet A** (registered as `github:<handle>`):

```text
submit_application(
  "genlayer-edu",
  "I created a substantive public contribution explaining GenLayer.",
  "https://github.com/torvalds/linux"
)
```

Expected revert:

```text
evidence_url must be hosted under the registered account on the registered
provider — expected something starting with https://github.com/<handle>/
```

**Record this transaction hash.** It is the single most useful artefact for the
resubmit note.

## T10 — Cross-provider, same handle

From **Wallet A**:

```text
submit_application(
  "genlayer-edu",
  "I created a substantive public contribution explaining GenLayer.",
  "https://medium.com/@<handle>/some-article"
)
```

Expected revert: same message as T9.

Record this hash too — T9 and T10 together cover both halves of the gap.

## T11 — Profile page is not its own evidence

From **Wallet A**:

```text
submit_application(
  "genlayer-edu",
  "I created a substantive public contribution explaining GenLayer.",
  "https://github.com/<handle>"
)
```

Expected revert: same message. The trailing `/` in the required prefix forces at
least one path segment after the account name.

## T12 — Malformed URL shapes

From **Wallet A**, each expected to revert with
`evidence_url contains a disallowed sequence`:

```text
https://github.com/<handle>/@evil.com/x
https://github.com/<handle>/../torvalds/linux
https://github.com/<handle>/repo\..\x
```

And expected to revert with `evidence_url must start with https://`:

```text
http://github.com/<handle>/repo
```

---

# Phase 4 — Positive path

## T13 — Successful submission

From **Wallet A**:

```text
submit_application(
  "genlayer-edu",
  "I wrote and published an original explainer on GenLayer intelligent contracts.",
  "https://github.com/<handle>/eligibility-judge"
)
```

Expected: `SUCCESS`

Verify:

```text
get_application_status("genlayer-edu", <Wallet A>)     → "PENDING"
get_application_evidence("genlayer-edu", <Wallet A>)   → the URL
is_evidence_used("genlayer-edu", "https://github.com/<handle>/eligibility-judge")   → true
is_evidence_used("genlayer-edu", "https://github.com/<handle>/eligibility-judge/")  → true
```

The last two lines matter: they differ only by a trailing slash and must both
return `true`. Before v0.2.17 the second returned `false`, which is what made the
per-campaign evidence burn bypassable.

## T14 — Positive adjudication

```text
judge_application("genlayer-edu", <Wallet A>)
```

Expected:

```text
get_application_status("genlayer-edu", <Wallet A>)   → "ELIGIBLE"
get_application_reason("genlayer-edu", <Wallet A>)   → non-empty explanation
```

Requires the evidence page to be publicly renderable, to visibly identify the
registered handle as owner, and to satisfy the campaign criteria.

## T15 — Already judged

```text
judge_application("genlayer-edu", <Wallet A>)
```

Expected revert:

```text
application already judged
```

---

# Phase 5 — Model layer, second campaign

Wallet A's slot in `genlayer-edu` is spent, so create a second campaign:

```text
create_campaign(
  "genlayer-edu-2",
  "GenLayer Education Bounty II",
  "Applicant must have created original educational content explaining GenLayer intelligent contracts."
)
```

## T16 — Fork under the correct account still fails authorship

Fork any third-party repository into Wallet A's GitHub account, then:

```text
submit_application(
  "genlayer-edu-2",
  "I created original educational content about GenLayer.",
  "https://github.com/<handle>/<forked-repo>"
)
judge_application("genlayer-edu-2", <Wallet A>)
```

The URL passes the deterministic gate — it *is* inside Wallet A's namespace. The
model layer is what must catch it, because the page shows "forked from …".

Expected: `NOT_ELIGIBLE`, with a reason referencing the fork or the original
author.

This is the defence-in-depth test. It is model-dependent rather than
deterministic, and should be described that way rather than as a guarantee.

## T17 — Unreachable evidence fails closed

Create a third campaign, then submit a URL inside the namespace that does not
resolve to real content:

```text
https://github.com/<handle>/this-repository-does-not-exist-9f3a
```

Expected: `NOT_ELIGIBLE`.

Note GitHub serves a rendered 404 page rather than an empty response, so the
verdict usually arrives via failed authorship or unmet criteria rather than via
the `FETCH_FAILED_*` branch. Either route is correct; only the final status is
asserted.

---

## Note on evidence anti-replay

`evidence_used` is retained and its keys are now canonicalised (query string,
fragment and trailing slashes stripped). In v0.2.17 it is **defence in depth
rather than an independently reachable branch**, because the namespace binding
already prevents the case it was written for:

- a second wallet cannot submit Wallet A's evidence URL — the URL is outside its
  own namespace, and handle uniqueness means no second wallet can hold
  `github:<handle>`;
- Wallet A cannot resubmit to the same campaign — `application_exists` blocks it
  first.

It is kept so the guarantee survives if the binding is ever relaxed, for example
to support a provider where the account is not part of the URL path.

---

## Known limitations

- **URL charset is conservative.** `_assert_safe_url` rejects `%` and `@`
  anywhere in the URL to keep the prefix test unspoofable. This also rejects
  otherwise-valid GitHub URLs containing percent-encoding, such as a file path
  with a space (`.../My%20Notes.md`). Use a URL without percent-encoding.
- **Handle reuse.** GitHub and X both allow a username to be released and
  re-claimed by a different person. The on-chain binding is permanent and does
  not track that.
- **Repository transfer.** A repository moved to another account after
  submission is caught by the model check, not deterministically.
- **The `x` provider.** Supported in code, but `x.com` serves a login wall to
  anonymous fetches, so both proof-of-control and evidence rendering will
  usually fail there. `github` is the working path in this version.

---

## Read methods

```text
get_handle(address)
get_provider(address)
get_wallet_of_handle(provider, handle)
get_expected_profile_url(provider, handle)
get_allowed_evidence_prefixes(address)          # new in v0.2.17
is_evidence_url_acceptable(address, url)        # new in v0.2.17
get_campaign_name(campaign_id)
get_campaign_criteria(campaign_id)
get_campaign_creator(campaign_id)
is_campaign_active(campaign_id)
is_evidence_used(campaign_id, evidence_url)
get_application_status(campaign_id, applicant)
get_application_description(campaign_id, applicant)
get_application_evidence(campaign_id, applicant)
get_application_reason(campaign_id, applicant)
```

---

## Resubmission consistency check

Before pressing **Resubmit**, verify every line:

```text
Studio source at 0xE1e340... line 1 reads          # v0.2.17
GitHub contract source == Studio source            byte-for-byte
README references                                  0xE1e340...
TESTING references                                 0xE1e340...
Submission evidence link 1 (Explorer)              0xE1e340...
Submission evidence link 2 (GitHub)                current commit
No file anywhere still references                  0xA71B49...
T9 and T10 transaction hashes recorded             for the resubmit note
```
