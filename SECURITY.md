# Security

greenbump edits code and runs a test suite, so it is worth being precise about what it protects
and what it does not.

## What greenbump protects

- **Your original repository.** greenbump copies the repository into a work directory and only
  ever edits the copy. The result is a patch file for a human to review.
- **Your secrets.** The test suite runs in a child process with a minimal environment: no
  tokens, no cloud credentials, no proxy settings, no inherited `PYTHONPATH`, and `HOME` pointed
  at the work copy. The model never sees an API key.
- **What the model can do.** The model can only call the eight tools in
  `src/greenbump/tools.py`. Paths are resolved inside the work copy and anything that escapes it,
  including through a symlink, is refused.
- **Cheating.** Edits to dependency, lock, CI and pytest config files are refused, and so are
  edits that skip or weaken tests, silence warnings, patch the library at runtime, or add process
  or network calls. A final verifier re-checks the whole diff with plain code before anything
  counts as a fix.
- **Prompt injection from changelogs.** Fetched changelogs are wrapped in `<untrusted>` tags,
  the model is told never to follow instructions inside them, and nothing in them can widen what
  the tools allow.

## What greenbump does not protect

- **It is not a sandbox.** The test suite, and therefore the upgraded library and every edit the
  model makes, runs as your user with network access. Only run greenbump on repositories you
  trust, or run it inside a container or a throwaway VM. A Docker runner with `--network none`
  is on the roadmap.
- **Guardrails are pattern based.** They catch the common shortcuts, not every possible one. The
  patch is meant for human review, never for automatic merge.

## Reporting a problem

Please open a GitHub security advisory on this repository rather than a public issue.

## If you commit a secret by mistake

1. Revoke or rotate the credential first. Removing it from git does not make it safe again.
2. Purge it from history with `git filter-repo` or BFG, then force-push.
3. Ask GitHub support to clear cached views if the repository is public.
