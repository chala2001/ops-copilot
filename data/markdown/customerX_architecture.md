# CustomerX Deployment Architecture

## Customer Overview
CustomerX is running WSO2 API Manager version 4.2.1.
Deployed on Azure Kubernetes Service (AKS) in the East US 2 region.
Namespace: customerx
Last updated: March 2025.
Environment: Production

## AKS Cluster Configuration
- Cluster name: customerx-aks-prod
- Kubernetes version: 1.28.3
- Node pool type: Standard_D4s_v3
- Node count: autoscaling enabled (minimum 2 nodes, maximum 8 nodes)
- OS disk size per node: 128 GB
- Region: East US 2
- Resource group: customerx-prod-rg

## WSO2 API Manager Details
- Version: 4.2.1
- Deployment mode: All-in-one (Gateway + Publisher + Developer Portal + Key Manager in one deployment)
- Docker image: wso2/wso2am:4.2.1
- Replicas: 3 (managed by HPA)
- Ports exposed: 9443 (HTTPS management), 8243 (HTTPS gateway), 8280 (HTTP gateway)

## Resource Allocation
- CPU request: 1000m (1 vCPU)
- CPU limit: 2000m (2 vCPU)
- Memory request: 2Gi
- Memory limit: 4Gi

## Networking and Ingress
- Internal DNS: customerx.wso2-sre.internal
- Publisher portal: https://customerx.wso2-sre.internal/publisher
- Developer portal: https://customerx.wso2-sre.internal/devportal
- Gateway endpoint: https://customerx.wso2-sre.internal:8243
- TLS certificate: Let's Encrypt, auto-renewed every 60 days
- Ingress class: nginx

## Database
- Type: Azure SQL Database
- Server: customerx-prod-sql.database.windows.net
- Database name: wso2amdb
- Tier: General Purpose, 4 vCores
- Backup retention: 14 days
- Geo-redundant backup: enabled

## Storage
- Azure Blob Storage account: customerxprodstorage
- Container: wso2-artifacts
- Used for: API artifacts, throttling policies, analytics data

## HPA (Horizontal Pod Autoscaler)
- Minimum replicas: 3
- Maximum replicas: 10
- CPU scale-up threshold: 70% average utilization
- Memory scale-up threshold: 80% average utilization
- Scale-down stabilization: 5 minutes

## Monitoring
- Azure Monitor: enabled
- Log Analytics workspace: customerx-logs
- Alert: CPU > 85% for 5 minutes → PagerDuty
- Alert: Pod restart count > 3 in 10 minutes → PagerDuty
- Alert: API Gateway latency P95 > 3000ms → email to SRE team

## Maintenance Window
- Schedule: Every Sunday, 02:00 AM to 04:00 AM UTC
- Blackout period: Last 5 days of each month (financial close)

## SLA
- Uptime target: 99.9% per month
- Maximum allowed downtime: 43 minutes per month
- RTO (Recovery Time Objective): 30 minutes
- RPO (Recovery Point Objective): 1 hour

## Known Issues
- SRE-1042: Throttling policy sync delay under high load.
  Symptoms: APIs return 429 errors despite quota not being exceeded.
  Workaround: Restart the gateway pod using kubectl rollout restart deployment/wso2-api-manager -n customerx
  Escalate to Team Lead if the issue persists after restart.
- SRE-1051: Memory usage spikes to 90%+ during peak hours (9 AM - 11 AM EST).
  Workaround: HPA automatically adds replicas. If memory limit is hit, manually increase limit temporarily.
  Root cause investigation ongoing with WSO2 support.

## Escalation Contacts
- Primary SRE: Jane Smith — jane.smith@wso2.com — +94 77 123 4567
- Secondary SRE: Bob Lee — bob.lee@wso2.com — +94 77 234 5678
- Customer Technical Lead: David Kumar — david.kumar@customerx.com
- WSO2 Support ticket: https://support.wso2.com (subscription ID: CX-2024-PRD-001)
