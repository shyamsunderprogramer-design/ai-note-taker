# ANT AI Note Taker - Deployment Guide
# Enterprise DevOps Pipeline Documentation

## Table of Contents

1. [Overview](#overview)
2. [Infrastructure Setup](#infrastructure-setup)
3. [CI/CD Pipeline](#cicd-pipeline)
4. [Deployment](#deployment)
5. [Monitoring](#monitoring)
6. [Rollback Procedures](#rollback-procedures)

---

## Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLOUD PROVIDER                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         KUBERNETES CLUSTER                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │   │
│  │  │   Ingress   │  │   Backend   │  │  Monitoring │                │   │
│  │  │  (NGINX/ALB)│  │  (3+ pods)  │  │  (Prometheus│                │   │
│  │  └─────────────┘  └─────────────┘  │   Grafana) │                │   │
│  │                                      └─────────────┘                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        DATA SERVICES                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │   │
│  │  │ PostgreSQL  │  │    Redis    │  │    Neo4j    │                │   │
│  │  │   (RDS)     │  │  (ElastiCache│  │  (GraphDB)  │                │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Infrastructure Setup

### Prerequisites

- Terraform >= 1.7.0
- kubectl >= 1.28
- Helm >= 3.14
- Azure CLI / AWS CLI / GCP SDK

### AWS EKS Setup

```bash
cd infrastructure/terraform/aws

# Initialize Terraform
terraform init -backend-config="bucket=your-terraform-state-bucket"

# Plan deployment
terraform plan -var="environment=production" -var="image_tag=v1.0.0"

# Apply infrastructure
terraform apply -var="environment=production" -var="image_tag=v1.0.0"

# Get kubeconfig
aws eks update-kubeconfig --name ant-cluster-production --region us-east-1
```

### Azure AKS Setup

```bash
cd infrastructure/terraform/azure

# Login to Azure
az login
az account set --subscription <subscription-id>

# Initialize Terraform
terraform init

# Plan and apply
terraform plan -var="environment=production"
terraform apply -var="environment=production"

# Get credentials
az aks get-credentials --name ant-aks-production --resource-group ant-production-rg
```

### GCP GKE Setup

```bash
cd infrastructure/terraform/gcp

# Initialize Terraform
terraform init -backend-config="bucket=your-tf-state-bucket"

# Plan and apply
terraform plan -var="project=your-project-id" -var="environment=production"
terraform apply -var="project=your-project-id" -var="environment=production"

# Get credentials
gcloud container clusters get-credentials ant-gke-production --zone us-central1-a
```

---

## CI/CD Pipeline

### Pipeline Stages

| Stage | Tools | Description |
|-------|-------|-------------|
| Lint | ESLint, Flake8, Checkov | Code quality + IaC scanning |
| Test | Pytest, Playwright | Unit, integration, E2E tests |
| Build | Docker, Buildx | Multi-architecture container builds |
| Scan | Trivy, Snyk, SonarQube | Security vulnerability scanning |
| Publish | GitHub Container Registry | Image push with SBOM |
| Deploy | Helm, ArgoCD | Kubernetes deployment |

### Security Gates

All gates must pass for deployment:

```yaml
security_gates:
  snyk:
    critical: 0
    high: 0
  trivy:
    critical: 0
    high: 5  # Allow some HIGH in dev
  sonarqube:
    bugs: 0
    vulnerabilities: 0
    security_hotspots: 0
  gitleaks:
    secrets: 0
```

---

## Deployment

### GitOps Flow (ArgoCD)

1. PR merges to `main` → ArgoCD detects change
2. ArgoCD syncs to staging automatically
3. After staging verification, promote to production

### Manual Deployment

```bash
# Deploy to staging
helm upgrade --install ant-backend \
  ./k8s/helm/backend \
  --namespace ant \
  --create-namespace \
  --values ./k8s/helm/backend/values-staging.yaml \
  --set image.tag=main-latest \
  --wait

# Deploy to production (with canary)
helm upgrade --install ant-backend \
  ./k8s/helm/backend \
  --namespace ant \
  --create-namespace \
  --values ./k8s/helm/backend/values-production.yaml \
  --set image.tag=v1.0.0 \
  --wait --atomic --cleanup-on-fail

# Canary rollout (Argo Rollouts)
kubectl argo rollouts set image ant-backend \
  ant-backend=ghcr.io/your-org/ant-backend:v1.0.0
```

---

## Monitoring

### Accessing Dashboards

```bash
# Port-forward to local
kubectl port-forward svc/prometheus 9090:9090 -n monitoring &
kubectl port-forward svc/grafana 3000:3000 -n monitoring &
```

### Key Metrics

| Metric | Alert | Threshold |
|--------|-------|-----------|
| Backend uptime | < 99.9% | Critical |
| API latency (p99) | > 2s | Warning |
| Error rate | > 1% | Warning |
| CPU usage | > 80% | Warning |
| Memory usage | > 90% | Warning |

### Log Aggregation

```bash
# View backend logs
kubectl logs -l app.kubernetes.io/name=ant-backend -n ant -f

# Search logs in Loki/Grafana
{kubernetes_namespace_name="ant"} |= "ERROR"
```

---

## Rollback Procedures

### Instant Rollback (Helm)

```bash
# List releases
helm history ant-backend -n ant

# Rollback to previous revision
helm rollback ant-backend -n ant

# Rollback to specific revision
helm rollback ant-backend 3 -n ant
```

### ArgoCD Rollback

```bash
# Via UI: Application → Details → History →rollback

# Via CLI
argocd app rollback ant-backend
```

### Emergency Stop

```bash
# Scale to zero (instant stop)
kubectl scale deployment ant-backend --replicas=0 -n ant

# Delete ingress (stop traffic)
kubectl delete ingress ant-backend-ingress -n ant
```

---

## Environment-Specific URLs

| Environment | URL | Notes |
|-------------|-----|-------|
| Staging | `https://api.staging.ant.example.com` | Auto-deploy from `main` |
| Production | `https://api.ant.example.com` | Manual approval |
| Preview | `https://api.pr-{number}.ant.example.com` | PR previews |
