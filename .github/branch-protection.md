# Branch Protection Rules - AI Note Taker

This document describes the recommended GitHub branch protection rules
for the AI Note Taker repository, aligned with DevOps governance best practices.

## `main` Branch (Production)

| Setting | Value |
|---------|-------|
| Require pull request before merging | **Yes** |
| Required approving reviews | **2** |
| Dismiss stale reviews on push | **Yes** |
| Require review from code owners | **Yes** |
| Require status checks to pass | **Yes** |
| Require branches to be up to date | **Yes** |
| Required status checks | `lint`, `test`, `container-build` |
| Require conversation resolution | **Yes** |
| Require signed commits | **Recommended** |
| Require linear history | **Yes** |
| Do not allow force pushes | **Yes** |
| Do not allow deletions | **Yes** |

## `develop` Branch (Integration)

| Setting | Value |
|---------|-------|
| Require pull request before merging | **Yes** |
| Required approving reviews | **1** |
| Dismiss stale reviews on push | **Yes** |
| Required status checks | `lint`, `test` |
| Require branches to be up to date | **No** |
| Do not allow force pushes | **No** (allow admins) |

## Feature Branches (`t*`, `phase*`)

| Setting | Value |
|---------|-------|
| Require pull request before merging | **No** (direct push allowed) |
| Required status checks | **None** |
| Allow force pushes | **Yes** (rebase-friendly) |

## CODEOWNERS File

Create `.github/CODEOWNERS`:

```
# Default owners
* @shyamsunderprogramer-design

# Backend code
/backend/ @shyamsunderprogramer-design

# Infrastructure
/.github/workflows/ @shyamsunderprogramer-design
/infrastructure/ @shyamsunderprogramer-design
/k8s/ @shyamsunderprogramer-design
/docker/ @shyamsunderprogramer-design

# Security
/backend/security/ @shyamsunderprogramer-design
/backend/core/config.py @shyamsunderprogramer-design
```

## Setting Up via GitHub CLI

```bash
# Set branch protection for main
gh api repos/shyamsunderprogramer-design/ai-note-taker/branches/main/protection \
  --method PUT \
  --field required_pull_request_reviews='{"required_approving_review_count":2,"dismiss_stale_reviews":true}' \
  --field required_status_checks='{"strict":true,"contexts":["lint","test","container-build"]}' \
  --field enforce_admins=true \
  --field restrictions=null

# Set branch protection for develop
gh api repos/shyamsunderprogramer-design/ai-note-taker/branches/develop/protection \
  --method PUT \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field required_status_checks='{"strict":false,"contexts":["lint","test"]}' \
  --field enforce_admins=false
```

## Required GitHub Secrets

Configure these in **Settings > Secrets and variables > Actions**:

| Secret | Description | Required For |
|--------|-------------|--------------|
| `GITHUB_TOKEN` | Auto-provided | All workflows |
| `SONAR_TOKEN` | SonarCloud analysis | CI |
| `SNYK_TOKEN` | Snyk dependency scanning | CI, Security |
| `AWS_ROLE_ARN` | OIDC role ARN for AWS | CD |
| `KUBE_CONFIG` | Kubernetes config | CD |
| `DD_API_KEY` | Datadog API key | CD (post-deploy) |
| `DD_APP_KEY` | Datadog app key | CD (post-deploy) |
| `SLACK_BOT_TOKEN` | Slack bot token | CD, Release |
| `JIRA_URL` | Jira instance URL | Release |
| `JIRA_TOKEN` | Jira auth token | Release |

### OIDC Setup for AWS

Instead of long-lived `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, use
**OIDC (OpenID Connect)** for GitHub Actions:

1. In AWS IAM, create an Identity Provider with URL `https://token.actions.githubusercontent.com`
2. Create an IAM Role with trust policy scoped to your repo and branch
3. Store the Role ARN as `AWS_ROLE_ARN` secret
4. The CD workflow uses `aws-actions/configure-aws-credentials@v4` with OIDC

No long-lived credentials needed — the role is assumed per-workflow-run via
short-lived tokens issued by GitHub's OIDC provider.