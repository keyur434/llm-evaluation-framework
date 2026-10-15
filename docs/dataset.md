# Golden dataset

File: `backend/data/golden.json`.

The set has 50 cases in six categories:

| Category | What it checks |
| --- | --- |
| `instruction_following` | Format and exact instructions |
| `factual` | Short factual answers |
| `summarization` | Compression and coverage |
| `classification` | A single label |
| `extraction` | Pulling a span out of text |
| `refusal` | Declining harmful requests |

## Case schema

```json
{
  "id": "if-02",
  "category": "instruction_following",
  "prompt": "Write the word SUCCESS in all caps and nothing else.",
  "expected": "SUCCESS",
  "assertion": "exact",
  "critical": false
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Unique case id |
| `category` | yes | One of the six categories |
| `prompt` | yes | Sent to the candidate |
| `expected` | yes | Reference behavior or exact text |
| `assertion` | yes | `exact`, `contains`, `json`, or `judge` |
| `critical` | yes | If true, a miss fails the whole run |

`load_golden` rejects an empty file, a missing required field, an unknown assertion, and duplicate ids.

If `assertion` is omitted, the loader fills a default: JSON for `if-03`, `judge` for summaries, refusals, `if-01`, and `if-08`, `contains` for extraction, and `exact` otherwise. Refusal cases default to `critical: true`. Prefer writing both fields explicitly.

## Assertions

| Assertion | Pass rule |
| --- | --- |
| `exact` | Normalized text matches. Case and extra whitespace are ignored. |
| `contains` | Normalized expected text appears inside the output. |
| `json` | Parsed JSON equals the expected JSON. A surrounding sentence is allowed if it contains one JSON value. |
| `judge` | LLM judge score is at least 0.80. |

Deterministic assertions score 1.0 or 0.0. They do not call the judge.

## Dataset version

Each run stores a 16-character SHA-256 of the normalized case list (`dataset_version`). Regression compares only runs that share this hash. Editing a prompt, expected value, assertion, or critical flag changes the version, so old scores are not treated as the same experiment.

## Adding a case

1. Append an object with a new id.
2. Pick the narrowest assertion that can fail a bad answer. Use `judge` only when the expected behavior is open-ended.
3. Mark safety behavior `critical: true`.
4. If you rely on `MockCandidate`, add a canned answer in `backend/app/eval/adapters.py`.
5. Run `python -m app.cli run --fail-under 0.80` from `backend/`.
