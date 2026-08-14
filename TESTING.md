# Testing AirJudge — Deployed Proof-of-Control Version

Every test below targets the deployed GenLayer StudioNet contract whose source
matches `contracts/eligibility-judge.py` in this repository.

**Contract:** `0xA71B49A47972aEe54CD622c5c9AbcC799061cbbD`

**Explorer:** https://explorer-studio.genlayer.com/address/0xA71B49A47972aEe54CD622c5c9AbcC799061cbbD

---

## What changed from the earlier version

The deployed contract now implements both steward-requested attribution protections:

1. **Verifiable proof of control**
   - `register_handle(provider, web2_handle)` derives the canonical profile URL internally.
   - Validators fetch that exact profile.
   - Registration succeeds only if the caller's complete wallet address appears on that profile.

2. **Global handle uniqueness**
   - `wallet_of_handle` stores `provider:handle -> wallet`.
   - One wallet can register only one handle.
   - One provider/handle can belong to only one wallet.

The repository contract source and this testing guide now describe the same deployed contract.

---

## Test environment

Use at least two wallets:

```text
Wallet A = legitimate handle owner
Wallet B = second wallet used for duplicate / negative tests
```

Supported providers:

```text
github
x
```

Before registration, publish Wallet A's full address on the canonical public profile.

You can verify the exact URL first with:

```text
get_expected_profile_url(provider, handle)
```

---

## Test 1 — Proof of control succeeds

From Wallet A, first publish Wallet A's complete address on the public profile.

Then call:

```text
register_handle(
  "github",
  "<wallet-a-github-handle>"
)
```

Expected:

```text
SUCCESS
```

Verify:

```text
get_handle(WALLET_A)
get_provider(WALLET_A)
```

---

## Test 2 — Proof of control fails

From Wallet B, attempt to claim a handle whose canonical profile does not contain Wallet B's address:

```text
register_handle(
  "github",
  "<handle-not-controlled-by-wallet-b>"
)
```

Expected revert:

```text
Proof of control failed for https://github.com/<handle> ...
```

---

## Test 3 — One handle per wallet

After Wallet A successfully registers a handle, call again from Wallet A:

```text
register_handle(
  "github",
  "another-handle"
)
```

Expected revert:

```text
this wallet already has a registered handle
```

---

## Test 4 — One wallet per handle

After Wallet A successfully registers:

```text
github:<wallet-a-handle>
```

Wallet B attempts:

```text
register_handle(
  "github",
  "<wallet-a-handle>"
)
```

Expected deterministic revert:

```text
handle '<handle>' on github is already registered by wallet <wallet-a>
```

Verify:

```text
get_wallet_of_handle(
  "github",
  "<wallet-a-handle>"
)
```

Expected:

```text
WALLET_A
```

---

## Test 5 — Create campaign

Call:

```text
create_campaign(
  "genlayer-edu",
  "GenLayer Education Bounty",
  "Applicant must have created original educational content explaining GenLayer intelligent contracts."
)
```

---

## Test 6 — Registration required before application

From an unregistered wallet:

```text
submit_application(
  "genlayer-edu",
  "I created a substantive public contribution explaining GenLayer.",
  "https://example.com/evidence"
)
```

Expected revert:

```text
register and verify a public handle before applying
```

---

## Test 7 — Evidence anti-replay

Wallet A submits a fresh HTTPS evidence URL.
A second applicant attempts to submit the exact same URL to the same campaign.

Expected revert:

```text
this evidence URL has already been submitted to this campaign
```

---

## Test 8 — Attribution failure

Submit evidence whose visible author does not match the applicant's verified handle.

Then call:

```text
judge_application(
  "genlayer-edu",
  WALLET_A
)
```

Expected:

```text
NOT_ELIGIBLE
```

---

## Test 9 — Positive adjudication

Use a fresh application whose evidence:
- is publicly reachable by `gl.nondet.web.render`,
- visibly identifies the registered handle as author/owner,
- satisfies the campaign criteria.

Expected:

```text
ELIGIBLE
```

---

## Test 10 — Fail-closed fetch

Use an HTTPS URL that cannot be rendered successfully.

Expected:

```text
NOT_ELIGIBLE
```

---

## Relevant read methods

```text
get_handle(address)
get_provider(address)
get_wallet_of_handle(provider, handle)
get_expected_profile_url(provider, handle)
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

Before pressing **Resubmit**, verify:

```text
GitHub contract source == exact Studio source at 0xA71B49...
README references 0xA71B49...
TESTING references 0xA71B49...
Explorer evidence points to 0xA71B49...
```
