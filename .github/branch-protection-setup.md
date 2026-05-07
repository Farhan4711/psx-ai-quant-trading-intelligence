# Branch Protection Setup

Configure these settings at:
https://github.com/Farhan4711/psx-ai-quant-trading-intelligence/settings/branches

## Rules for `main` branch

Go to **Settings → Branches → Add branch protection rule**, pattern: `main`

- [x] **Require a pull request before merging**
  - Required approvals: 1 (or 0 if solo — but still require a PR to force CI to run)
  - Dismiss stale pull request approvals when new commits are pushed: yes
- [x] **Require status checks to pass before merging**
  - Require branches to be up to date before merging: yes
  - Required status checks to add (add these once the first CI run completes):
    - `lint-and-typecheck` (api-ci)
    - `test` (api-ci)
    - `lint-and-typecheck` (web-ci)
    - `test` (web-ci)
    - `lint-and-typecheck` (ingest-ci)
- [x] **Require conversation resolution before merging**
- [x] **Do not allow bypassing the above settings** (uncheck "Allow force pushes" and "Allow deletions")

## Why this matters

Without branch protection, a bad push to `main` can break production. With it:
- CI must pass before any merge
- Even as a solo founder, the PR flow forces a review moment before every change ships
- Force-push to main is blocked (protects against accidental `git push --force`)
