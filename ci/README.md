# Pending GitHub Actions workflows

These workflows are ready, but the Claude GitHub app can't write to `.github/workflows/` without the `workflows` permission.

To activate them, do one of the following:
- **From any machine with push access:**
  ```bash
  git mv ci/workflows .github/workflows && git commit -m "ci: activate workflows" && git push
  ```
- **Grant the permission:** give the Claude GitHub app the *Workflows* permission (GitHub → Settings → Applications → Claude → Configure). Then ask an agent to move them.

| File | Purpose |
|---|---|
| `ci.yml` | Path-filtered PR/push checks. `ci-ok` is the single required check. |
| `pr-title.yml` | Enforces Conventional Commit PR titles. |
| `pages.yml` | Manual docs/demo deploy to GitHub Pages. |
