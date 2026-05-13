# CustomerY SRE Runbook

## Runbook Overview
This runbook covers incident response procedures for CustomerY production environment.
Customer: CustomerY | Environment: Production | Region: West Europe
Last reviewed: February 2025 | Reviewed by: Sarah Johnson

---

## Incident: Slow API response (P95 latency > 5 seconds)

**Ticket reference:** SRE-1067
**Severity:** P2 (service degraded)
**Trigger condition:** Occurs when total subscription count exceeds 10,000

### Diagnosis steps
1. Check current subscription count:
   kubectl exec -it deployment/wso2-api-manager -n customery -- curl -sk https://localhost:9443/api/am/admin/v3/subscriptions -u admin | python3 -c "import sys,json; d=json.load(sys.stdin); print('Count:', d.get('count'))"
2. Check P95 latency in Azure Monitor for customery-logs workspace.
3. Check API Manager heap usage:
   kubectl exec -it <pod-name> -n customery -- jstat -gcutil 1 3

### Fix
Restart API Manager pods to flush subscription cache:
  kubectl rollout restart deployment/wso2-api-manager -n customery
  kubectl rollout status deployment/wso2-api-manager -n customery

Verify latency recovers within 5 minutes. Check developer portal loads correctly:
  curl -sk https://customery.wso2-sre.internal/devportal | grep -i wso2

### Long-term fix
Upgrade to WSO2 API Manager 4.2.1 (scheduled Q3 2025). Raise with Sarah Johnson for planning.

---

## Incident: TLS certificate expired or near expiry

**Ticket reference:** SRE-1073
**Severity:** P1 if expired, P3 if < 10 days remaining

### Check certificate expiry
  kubectl get certificate -n customery
  kubectl describe certificate wso2am-tls -n customery | grep -E "Not After|Renewal"

### Manual renewal if cert-manager not auto-renewing
  kubectl delete certificate wso2am-tls -n customery
  kubectl apply -f /home/chalaka/ops-copilot_gemini/k8s/customery-certificate.yaml

### Verify renewal
  kubectl get certificate -n customery
  # Status should show Ready: True

### Monthly check (run on 25th of each month)
  kubectl get certificate -n customery -o jsonpath='{.items[*].status.notAfter}'

---

## Incident: Pod OOMKilled (Out Of Memory)

**Severity:** P2

### Diagnosis
1. Check which pods were OOMKilled:
   kubectl get pods -n customery
   kubectl describe pod <pod-name> -n customery | grep -A5 OOMKilled
2. Check current resource usage:
   kubectl top pods -n customery

### Fix
Delete the crashed pod (Kubernetes will restart it):
  kubectl delete pod <pod-name> -n customery

If OOMKills are repeated, temporarily increase memory limit by patching:
  kubectl patch deployment wso2-api-manager -n customery -p '{"spec":{"template":{"spec":{"containers":[{"name":"wso2am","resources":{"limits":{"memory":"4Gi"}}}]}}}}'

### Escalation
If OOMKills happen more than 3 times in 1 hour, call Sarah Johnson.

---

## Routine: Verifying CustomerY cluster health

  kubectl get nodes                              # all nodes Ready
  kubectl get pods -n customery                  # all pods Running, no restarts
  kubectl top pods -n customery                  # check memory stays below 3Gi limit
  kubectl get hpa -n customery                  # check replica count and CPU %
  kubectl get certificate -n customery           # TLS cert Ready and not expiring soon

---

## Routine: Checking CustomerY database connectivity

  kubectl exec -it deployment/wso2-api-manager -n customery -- \
    curl -sk "jdbc:sqlserver://customery-prod-sql.database.windows.net:1433;databaseName=wso2amdb_y"

If database is unreachable, check Azure SQL firewall rules allow AKS subnet 10.2.0.0/16.
Contact: Emma Wilson (emma.wilson@customery.com) for database-level access.
