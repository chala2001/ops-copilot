# CustomerZ Deployment Architecture

## Customer Overview
CustomerZ is running WSO2 API Manager version 4.3.0.
Deployed on Azure Kubernetes Service (AKS) in the Southeast Asia region.
Namespace: customerz
Last updated: April 2025.
Environment: Production
Note: CustomerZ is the largest deployment managed by the WSO2 SRE Sri Lanka team.

## AKS Cluster Configuration
- Cluster name: customerz-aks-prod
- Kubernetes version: 1.29.1
- Node pool type: Standard_D8s_v3
- Node count: autoscaling enabled (minimum 3 nodes, maximum 12 nodes)
- OS disk size per node: 256 GB
- Region: Southeast Asia (Singapore)
- Resource group: customerz-prod-rg

## WSO2 API Manager Details
- Version: 4.3.0
- Deployment mode: Distributed (Gateway and Control Plane deployed separately)
- Gateway image: wso2/wso2am-gateway:4.3.0
- Control Plane image: wso2/wso2am:4.3.0
- Gateway replicas: 5 (managed by HPA)
- Control Plane replicas: 2
- Ports exposed: 9443 (HTTPS control plane), 8243 (HTTPS gateway), 8280 (HTTP gateway)

## Resource Allocation (Gateway pods)
- CPU request: 2000m (2 vCPU)
- CPU limit: 4000m (4 vCPU)
- Memory request: 4Gi
- Memory limit: 8Gi

## Resource Allocation (Control Plane pods)
- CPU request: 1000m (1 vCPU)
- CPU limit: 2000m (2 vCPU)
- Memory request: 2Gi
- Memory limit: 4Gi

## Networking and Ingress
- Internal DNS: customerz.wso2-sre.internal
- Publisher portal: https://customerz.wso2-sre.internal/publisher
- Developer portal: https://customerz.wso2-sre.internal/devportal
- Gateway endpoint: https://customerz.wso2-sre.internal:8243
- TLS certificate: WSO2 internal CA (not Let's Encrypt — customerz has their own CA)
- Ingress class: nginx
- WAF (Web Application Firewall): Azure WAF enabled in front of ingress

## Database
- Type: Azure Cosmos DB (NoSQL) — different from other customers
- Account name: customerz-cosmos-prod
- API type: Core (SQL)
- Consistency level: Session
- Backup: Continuous backup enabled (point-in-time restore up to 30 days)
- Regions: Southeast Asia (primary), East Asia (secondary — geo-redundant)

## Storage
- Azure Blob Storage account: customerzprodstorage
- Container: wso2-artifacts
- Redundancy: RA-GZRS (geo-zone redundant)

## HPA (Horizontal Pod Autoscaler)
- Gateway minimum replicas: 5
- Gateway maximum replicas: 20
- CPU scale-up threshold: 60% average utilization
- Memory scale-up threshold: 75% average utilization
- Scale-down stabilization: 15 minutes

## Monitoring
- Azure Monitor: enabled
- Log Analytics workspace: customerz-logs
- Datadog integration: enabled (agent deployed as DaemonSet)
- PagerDuty integration: all P1 and P2 alerts
- Alert: Gateway latency P99 > 2000ms → PagerDuty immediate
- Alert: CPU > 80% for 3 minutes → PagerDuty
- Alert: Any pod CrashLoopBackOff → PagerDuty immediate

## Maintenance Window
- Schedule: Every Sunday, 04:00 AM to 06:00 AM UTC (Singapore: Sunday 12 noon)
- Blackout period: First 3 days of every month (billing cycle)
- Change freeze: December 20 to January 5 (end-of-year freeze)

## SLA
- Uptime target: 99.95% per month
- Maximum allowed downtime: 21 minutes per month
- RTO (Recovery Time Objective): 15 minutes
- RPO (Recovery Point Objective): 30 minutes
- CustomerZ has financial penalties for SLA breach above 30 minutes downtime

## Known Issues
- SRE-1089: Azure Cosmos DB connection pool exhaustion during burst traffic (> 5000 req/sec).
  Symptoms: "RequestRateTooLargeException" in gateway logs, API calls timeout.
  Workaround: Increase Cosmos DB Request Units (RUs) temporarily via Azure portal.
  Target: 50,000 RU/s during burst, 20,000 RU/s baseline.
  Long-term fix: Implement local caching layer (Redis) — in design phase.
- SRE-1094: WAF occasionally blocks legitimate API calls with large JWT tokens (> 8KB).
  Workaround: Add specific API paths to WAF exclusion list in Azure portal.
  Contact Alex Wong before modifying WAF rules.

## Escalation Contacts
- Primary SRE: Alex Wong — alex.wong@wso2.com — +94 77 567 8901
- Secondary SRE: Priya Nair — priya.nair@wso2.com — +94 77 678 9012
- Customer Technical Lead: James Tan — james.tan@customerz.com — +65 98 765 4321
- WSO2 Support ticket: https://support.wso2.com (subscription ID: CZ-2025-PRD-003)
- Datadog support: customerz-datadog@wso2-internal.com
