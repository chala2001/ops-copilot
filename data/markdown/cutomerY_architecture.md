;# CustomerY Deployment Architecture
 
## Customer Overview
CustomerY is running WSO2 API Manager version 4.3.3.
Deployed on Azure Kubernetes Service (AKS) in  US  region.
Last updated: March 2026.
 
## AKS Configuration
- Node pool type: Standard_D4s_v3
- Autoscaling: enabled (min: 2 nodes, max: 8 nodes)
- OS disk: 128 GB
- Kubernetes version: 1.28.7
 
## Known Issues
- SRE-1042: Throttling policy sync delay under high load.
  Workaround: Restart the gateway pod. Escalate to Team Lead if persists.
 
## Escalation Contacts
- Primary: Jane Smith (jane@wso2.com)
- Secondary: Bob Lee (bob@wso2.com)
