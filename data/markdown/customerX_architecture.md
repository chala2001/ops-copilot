# CustomerX Deployment Architecture
 
## Customer Overview
CustomerX is running WSO2 API Manager version 4.2.1.
Deployed on Azure Kubernetes Service (AKS) in East US 2 region.
Last updated: March 2025.
 
## AKS Configuration
- Node pool type: Standard_D4s_v3
- Autoscaling: enabled (min: 2 nodes, max: 8 nodes)
- OS disk: 128 GB
- Kubernetes version: 1.28.3
 
## Known Issues
- SRE-1042: Throttling policy sync delay under high load.
  Workaround: Restart the gateway pod. Escalate to Team Lead if persists.
 
## Escalation Contacts
- Primary: Jane Smith (jane@wso2.com)
- Secondary: Bob Lee (bob@wso2.com)
