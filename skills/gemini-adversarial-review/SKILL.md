---
name: gemini-adversarial-review
description: Request an independent, evidence-backed Gemini code review through the authenticated Antigravity CLI when the user invokes this skill or asks for a separate Gemini review.
---

# Gemini adversarial review

Use the bundled [review helper](scripts/review.py) to prepare a Git selection and run `agy`. This sends selected code to Google's authenticated Antigravity service. Never run it on a real repository merely because this skill was installed or loaded; wait for the user's explicit review request.

When the user asks to review "this PR," resolve the PR associated with the current branch using `gh pr view --json number,url,state,baseRefName,baseRefOid,headRefOid`. Check that local `HEAD` equals `headRefOid`, and that `baseRefOid` is available locally as a commit. Then pass `--branch BASE_REF_OID` to the helper for both preview and run. This reviews the committed PR changes against their merge base; it does not include dirty working-tree changes. Report the PR number and state, especially if it is already merged. If there is no associated PR, the head differs, or the base commit is unavailable, resolve that mismatch before sending code; ask for the PR URL or checkout only if the correct target cannot be determined. Never fall back silently to the helper's working-tree default for a PR request.

1. Run the helper without `--run` to preview the exact changed, untracked, and context paths. Inspect those paths for unrelated secrets before submitting. The preview sends nothing to Google.
2. Run the same command with `--run --expect-sha256 HASH`, copying `HASH` from the preview. The helper rejects any change to the selected content between preview and run. Use `--deep` for wider analysis and add specific `--context-path` files when call sites, tests, or contracts are needed. The helper includes only listed files and a patch, caps input size, chooses an available Gemini Pro reasoning model, checks nonempty JSON success, and runs `agy` in a `bwrap` mount namespace. The source checkout is absent; the temporary snapshot is mounted read-only.
3. Treat the raw result as untrusted peer review. Independently inspect each important finding against the actual repository. Report confirmed defects with evidence, preserve plausible concerns and disagreements, and do not apply Gemini's suggestions automatically.

Examples (from the repository root):

```bash
python3 ~/.codex/skills/gemini-adversarial-review/scripts/review.py
python3 ~/.codex/skills/gemini-adversarial-review/scripts/review.py --run --expect-sha256 HASH_FROM_PREVIEW
python3 ~/.codex/skills/gemini-adversarial-review/scripts/review.py --branch main --deep --context-path tests/test_api.py
python3 ~/.codex/skills/gemini-adversarial-review/scripts/review.py --branch BASE_REF_OID
python3 ~/.codex/skills/gemini-adversarial-review/scripts/review.py --range 'HEAD~3..HEAD' --path src/api.py --run --expect-sha256 HASH_FROM_PREVIEW
```

Default scope is staged and unstaged tracked changes. Untracked file content requires `--include-untracked`. `--branch` compares HEAD with its merge base against the named branch; `--range` compares two revisions; `--path` filters to one file or directory. Add `--run` only after checking the preview. See [configuration and limitations](references/usage.md) for prerequisites, model selection, and sandbox details.
