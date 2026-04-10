# ANT AI Note Taker - Security & Compliance Guide

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EDGE / WAF                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CloudArmor / Azure Firewall / GCP Security Policy                   │   │
│  │  - Rate limiting                                                      │   │
│  │  - OWASP Top 10 protection                                           │   │
│  │  - DDoS mitigation                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        INGRESS (NGINX / ALB / Cloud LB)              │   │
│  │  - TLS 1.3 termination                                               │   │
│  │  - Certificate management (cert-manager)                              │   │
│  │  - WebSocket support                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         KUBERNETES CLUSTER                            │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐                          │   │
│  │  │ NetworkPolicy│ │ PodSecurity │ │ RBAC    │                          │   │
│  │  │ (calico)   │ │ (PSA)     │ │ (OIDC)   │                          │   │
│  │  └───────────┘ └───────────┘ └───────────┘                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          APPLICATION                                 │   │
│  │  - mTLS between services (Istio)                                    │   │
│  │  - JWT authentication                                                │   │
│  │  - Rate limiting                                                     │   │
│  │  - Input validation                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Secret Management

### AWS Secrets Manager

```yaml
# terraform/aws/main.tf
resource "aws_secretsmanager_secret" "backend" {
  name = "ant/backend-secrets"

  recovery_window_in_days = 7  # 0 for immediate, use with caution
}

# Auto-rotate every 30 days
resource "aws_secretsmanager_secret_rotation" "backend" {
  secret_id = aws_secretsmanager_secret.backend.id

  rotation_lambda_arn = aws_lambda_function.rotation.arn

  rotation_rules {
    automatically_after_days = 30
  }
}
```

### Azure Key Vault

```bash
# terraform/azure/main.tf
resource "azurerm_key_vault" "main" {
  name                = "ant-kv-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name

  purge_protection_enabled = var.environment == "production"
  soft_delete_retention_days = 7

  # RBAC for secret access
  sku_name = "premium"
}
```

### GCP Secret Manager

```yaml
# terraform/gcp/main.tf
resource "google_secret_manager_secret" "database_url" {
  secret_id = "ant-database-url"

  replication {
    auto {}
  }
}
```

---

## Compliance Checklist

### HIPAA (if handling PHI)

- [ ] Business Associate Agreement (BAA) with cloud provider
- [ ] Encryption at rest (AES-256)
- [ ] Encryption in transit (TLS 1.2+)
- [ ] Audit logging
- [ ] Access controls
- [ ] Data backup and recovery
- [ ] Incident response plan

### SOC 2 Type II

- [ ] Access management
- [ ] Change management
- [ ] Monitoring and logging
- [ ] Incident response
- [ ] Risk assessment

---

## Security Scanning Schedule

| Scan | Frequency | Tool | Fail Gate |
|------|-----------|------|-----------|
| Secrets | Every push | GitLeaks | Yes (Critical/High) |
| SAST | Every PR | SonarQube | Yes |
| SCA | Daily | Snyk | Yes (Critical/High) |
| Container | Every build | Trivy | Yes (Critical only) |
| IaC | Every PR | Checkov | Yes |
| Runtime | Always | Falco | Alert only |

---

## Incident Response

### Severity Levels

| Level | Definition | Response Time | Examples |
|-------|-----------|---------------|---------|
| P1 | Critical - Service down | 15 min | DB breach, data loss |
| P2 | High - Major feature broken | 1 hour | Auth failure |
| P3 | Medium - Degraded | 4 hours | High latency |
| P4 | Low - Minor issue | 24 hours | UI glitch |

### Response Procedure

1. **Detect** → Alert fired from monitoring
2. **Triage** → Assess severity and impact
3. **Communicate** → Notify stakeholders
4. **Mitigate** → Apply fix or rollback
5. **Resolve** → Deploy permanent fix
6. **Review** → Post-mortem analysis
