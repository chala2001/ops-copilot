# General SRE Procedures — WSO2 Sri Lanka Branch

## Document Purpose
This document contains general SRE procedures applicable across all customer environments
managed by the WSO2 Sri Lanka SRE team.
Last updated: April 2025 | Owner: SRE Team Lead

---

## On-Call Rotation

The WSO2 SRE Sri Lanka team operates a weekly on-call rotation.
- Primary on-call: rotates each Monday 09:00 AM IST
- Secondary on-call: backup if primary is unreachable within 5 minutes
- Current rotation schedule is maintained in PagerDuty (team: wso2-sre-lk)

On-call responsibilities:
- Respond to PagerDuty alerts within 5 minutes during business hours
- Respond within 15 minutes outside business hours
- Escalate unresolved P1 incidents to Team Lead within 30 minutes

Team Lead: Chalaka Perera — chalaka@wso2.com — +94 77 900 0001

---

## Incident Severity Definitions

P1 — Critical (full outage or SLA breach imminent):
  Response time: 5 minutes. Call on-call SRE directly.
  Examples: all pods down, database unreachable, 100% error rate

P2 — High (service degraded, partial failure):
  Response time: 15 minutes. PagerDuty alert.
  Examples: high latency, one pod CrashLoopBackOff, partial errors

P3 — Medium (non-critical issue, workaround available):
  Response time: 4 hours. Create JIRA ticket.
  Examples: certificate expiring in 7 days, non-critical alert firing

P4 — Low (cosmetic or informational):
  Response time: next business day.

---

## Standard kubectl Commands

Check all namespaces for pod health:
  kubectl get pods --all-namespaces | grep -v Running

Get pod resource usage across all customer namespaces:
  kubectl top pods -n customerx
  kubectl top pods -n customery
  kubectl top pods -n customerz

Check recent events (last 30 minutes) across all namespaces:
  kubectl get events --all-namespaces --sort-by=.lastTimestamp | tail -30

Describe a failing pod for diagnosis:
  kubectl describe pod <pod-name> -n <namespace>

Get logs from previous container (after crash):
  kubectl logs <pod-name> -n <namespace> --previous

Force delete a stuck pod:
  kubectl delete pod <pod-name> -n <namespace> --grace-period=0 --force

---

## WSO2 API Manager Admin Password

Default admin username: admin
The admin password is stored per customer in Azure Key Vault:
- CustomerX: keyvault name = customerx-prod-kv, secret name = wso2am-admin-password
- CustomerY: keyvault name = customery-prod-kv, secret name = wso2am-admin-password
- CustomerZ: keyvault name = customerz-prod-kv, secret name = wso2am-admin-password

To retrieve a password (requires Azure RBAC permission):
  az keyvault secret show --vault-name customerx-prod-kv --name wso2am-admin-password --query value -o tsv

---

## Checking WSO2 API Manager version inside a pod

  kubectl exec -it deployment/wso2-api-manager -n <namespace> -- cat /home/wso2carbon/wso2am-*/repository/conf/carbon.xml | grep -i version

Or check the Docker image label:
  kubectl get deployment wso2-api-manager -n <namespace> -o jsonpath='{.spec.template.spec.containers[0].image}'

---

## Azure Resource Group Summary

| Customer  | Resource Group       | AKS Cluster             | Region         |
|-----------|---------------------|-------------------------|----------------|
| CustomerX | customerx-prod-rg   | customerx-aks-prod      | East US 2      |
| CustomerY | customery-prod-rg   | customery-aks-prod      | West Europe    |
| CustomerZ | customerz-prod-rg   | customerz-aks-prod      | Southeast Asia |

---

## Accessing AKS clusters

Get AKS credentials (run once per cluster):
  az aks get-credentials --resource-group customerx-prod-rg --name customerx-aks-prod
  az aks get-credentials --resource-group customery-prod-rg --name customery-aks-prod
  az aks get-credentials --resource-group customerz-prod-rg --name customerz-aks-prod

Switch between clusters:
  kubectl config use-context customerx-aks-prod
  kubectl config use-context customery-aks-prod
  kubectl config use-context customerz-aks-prod

---

## Post-incident Review Process

After every P1 or repeated P2:
1. Write an incident report within 24 hours using the template in Confluence (SRE-POSTMORTEM-TEMPLATE)
2. Identify root cause — use the 5 Whys technique
3. Create JIRA tickets for each action item
4. Present at next weekly SRE sync (every Wednesday 10:00 AM IST)
