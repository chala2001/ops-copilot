# CustomerZ SRE Runbook

## Runbook Overview
This runbook covers incident response procedures for CustomerZ production environment.
Customer: CustomerZ | Environment: Production | Region: Southeast Asia (Singapore)
Last reviewed: April 2025 | Reviewed by: Alex Wong
IMPORTANT: CustomerZ has financial SLA penalties. Any outage must be reported within 15 minutes.

---

## Incident: Cosmos DB connection pool exhaustion (RequestRateTooLargeException)

**Ticket reference:** SRE-1089
**Severity:** P1 (response times will degrade rapidly)
**Trigger condition:** Burst traffic above 5000 requests per second

### Diagnosis steps
1. Check gateway logs for the error:
   kubectl logs deployment/wso2-gateway -n customerz | grep RequestRateTooLargeException | tail -20
2. Check current Cosmos DB RU consumption in Azure Portal:
   Azure Portal → customerz-cosmos-prod → Metrics → Total Request Units
3. Check current gateway throughput:
   kubectl top pods -n customerz

### Immediate fix
Scale up Cosmos DB RUs temporarily:
1. Open Azure Portal → customerz-cosmos-prod → Scale
2. Increase from 20,000 RU/s to 50,000 RU/s
3. Confirm and wait 2 minutes for change to propagate
4. Monitor error rate in Datadog dashboard

### Scale back down after incident
After traffic normalises (usually 2-4 hours):
1. Azure Portal → customerz-cosmos-prod → Scale
2. Return to 20,000 RU/s baseline

### Escalation
Immediately call Alex Wong (+94 77 567 8901). This is a P1 — do not wait.
If Cosmos DB scaling does not resolve in 10 minutes, engage Azure Premium Support.

---

## Incident: WAF blocking legitimate API calls

**Ticket reference:** SRE-1094
**Severity:** P2

### Symptoms
Specific API endpoints return 403 Forbidden. Gateway logs show:
  "Request blocked by Azure WAF rule [rule-id]"

### Diagnosis
1. Check WAF logs in Azure Monitor:
   Azure Portal → customerz-prod-rg → Application Gateway → WAF Logs
2. Identify the blocked rule ID and affected API path.

### Fix — Add WAF exclusion
Contact Alex Wong BEFORE changing WAF rules. Then:
1. Azure Portal → Application Gateway → WAF policy → Exclusions
2. Add exclusion for the specific rule ID and API path
3. Document the exclusion in the WAF change log (Confluence: CZ-WAF-CHANGES)

---

## Incident: Gateway pod CrashLoopBackOff

**Severity:** P1 — triggers PagerDuty immediately

### Diagnosis steps
1. Check pod status:
   kubectl get pods -n customerz
2. Check crash reason:
   kubectl describe pod <pod-name> -n customerz
   kubectl logs <pod-name> -n customerz --previous
3. Check if Control Plane is reachable from gateway:
   kubectl exec -it <gateway-pod> -n customerz -- curl -sk https://wso2am-cp-service:9443/services/APIKeyValidationService

### Fix
If crash is due to Control Plane unreachable:
  kubectl rollout restart deployment/wso2-controlplane -n customerz

If crash is due to OOMKill (memory limit 8Gi exceeded):
  kubectl patch deployment wso2-gateway -n customerz \
    -p '{"spec":{"template":{"spec":{"containers":[{"name":"wso2am-gateway","resources":{"limits":{"memory":"12Gi"}}}]}}}}'

### SLA reporting
CustomerZ has a 15-minute reporting obligation. Notify James Tan (james.tan@customerz.com) immediately for any P1.

---

## Routine: CustomerZ health check (run every morning 9 AM SGT)

  kubectl get nodes                                      # all nodes Ready
  kubectl get pods -n customerz                          # all pods Running
  kubectl top pods -n customerz                          # memory below 8Gi per gateway pod
  kubectl get hpa -n customerz                          # gateway replicas and CPU %
  kubectl logs deployment/wso2-gateway -n customerz --since=1h | grep -i error | wc -l

Expected: error count in last 1 hour should be below 50. Above 100 = investigate.

---

## Routine: Scaling gateway replicas manually

CustomerZ may need manual scaling before known high-traffic events (product launches, year-end).
  kubectl scale deployment/wso2-gateway -n customerz --replicas=15

Always notify Alex Wong and James Tan before manual scaling events.
