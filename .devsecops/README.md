# ANT AI Note Taker - Enterprise DevSecOps Pipeline

## Overview
This repository follows GitOps principles with enterprise-grade CI/CD, security scanning, and multi-cloud deployment capabilities.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CI/CD PIPELINE FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │   LINT   │───▶│   TEST   │───▶│  BUILD   │───▶│  SCAN    │              │
│  │  Stage   │    │  Stage   │    │  Stage   │    │  Stage   │              │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
│       │              │              │              │                       │
│  • ESLint         • Pytest       • Docker       • Trivy                     │
│  • Flake8        • Coverage     • Multi-arch   • Snyk                       │
│  • Pre-commit    • Integration  • Helm chart   • SonarQube                   │
│  • TFLint        • E2E          • SBOM gen     • Falco                      │
│                                     │              │                       │
│                                     ▼              ▼                       │
│                              ┌──────────┐    ┌──────────┐                   │
│                              │  ARTIFACT│    │ SECURITY │                   │
│                              │  PUSH    │    │ GATE     │                   │
│                              └──────────┘    └──────────┘                   │
│                                     │              │                       │
│                                     ▼              ▼                       │
│                              ┌─────────────────────────────────┐           │
│                              │      DEPLOYMENT STAGE           │           │
│                              │  • Staging (Auto)               │           │
│                              │  • Production (Manual)          │           │
│                              │  • Blue-Green / Canary         │           │
│                              └─────────────────────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
.devsecops/
├── .github/
│   └── workflows/
│       ├── ci.yml              # Main CI pipeline
│       ├── cd.yml              # CD deployment pipeline
│       ├── security.yml         # Security scanning pipeline
│       ├── release.yml          # Release management
│       ├── infrastructure/      # Cloud-specific IaC
│       │   ├── aws/            # AWS EKS deployment
│       │   ├── azure/          # Azure AKS deployment
│       │   └── gcp/            # GCP GKE deployment
│       └── security/           # Security workflows
│           ├── snyk.yml        # Snyk dependency scanning
│           ├── sonarqube.yml   # Code quality gates
│           └── trivy.yml       # Container scanning
├── docker/
│   ├── Dockerfile.backend      # Multi-stage backend image
│   ├── Dockerfile.electron     # Electron app image
│   └── docker-compose.yml      # Local development
├── k8s/
│   ├── base/                   # K8s base manifests
│   └── helm/                   # Helm charts
└── infrastructure/
    └── terraform/              # IaC for all clouds
```

## Security Gates

All security gates must pass before deployment:

| Gate | Tool | Threshold |
|------|------|-----------|
| SAST | SonarQube | 0 Critical, 0 High bugs |
| SCA | Snyk | 0 Critical/High vulnerabilities |
| Container | Trivy | 0 Critical vulnerabilities |
| IaC | Checkov/Tfsec | 0 High/Critical findings |
| Secrets | GitLeaks | 0 secrets detected |
| License | FOSSA | No blacklisted licenses |

## Environments

- **Dev**: Auto-deploy on PR merge to `develop`
- **Staging**: Auto-deploy on merge to `main`
- **Production**: Manual approval + canary rollout

## Quick Links

- [Security Policy](./.devsecops/SECURITY.md)
- [Deployment Guide](./.devsecops/DEPLOYMENT.md)
- [Helm Values](./k8s/helm/values.yaml)
