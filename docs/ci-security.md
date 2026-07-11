# CI security checks

The following checks are required and fail CI when they find a violation:

- Gitleaks scans repository history for committed secrets.
- Hadolint rejects warnings or errors in both Dockerfiles.
- actionlint validates GitHub Actions workflow syntax and expressions.
- `uv audit --frozen` checks the locked Python dependency graph for known vulnerabilities without changing the lockfile.
- Dependency Review blocks pull requests that introduce vulnerable dependencies.
- Trivy blocks application and migration images containing fixed high- or critical-severity vulnerabilities.

Dependabot update proposals and the SonarCloud and Snyk badges are advisory maintenance signals, not merge-blocking CI jobs.

Suppress a required finding only when it is a confirmed false positive or an accepted risk. Keep the exception as narrow as possible and document its reason, affected identifier, owner, and review date next to the tool-specific configuration.
