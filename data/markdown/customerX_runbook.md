# CustomerX SRE Runbook

## Runbook Overview
This runbook covers incident response procedures for CustomerX production environment.
Customer: CustomerX | Environment: Production | Region: East US 2
Last reviewed: March 2025 | Reviewed by: Jane Smith

---

## Incident: API Gateway returning 429 (Too Many Requests) errors

**Ticket reference:** SRE-1042
**Severity:** P2 (service degraded, not fully down)

### Diagnosis steps
1. Check throttling policy sync status:
   kubectl exec -it deployment/wso2-api-manager -n customerx -- curl -sk https://localhost:9443/throttle/data/v1/config -u admin:admin123
2. Check gateway pod logs for "ThrottlingDataRetriever" errors:
   kubectl logs deployment/wso2-api-manager -n customerx | grep ThrottlingDataRetriever
3. Check traffic manager connectivity:
   kubectl exec -it deployment/wso2-api-manager -n customerx -- curl -sk https://localhost:9443/services/ThrottleDataRetriever

### Fix
Restart the gateway pod to force policy re-sync:
  kubectl rollout restart deployment/wso2-api-manager -n customerx
  kubectl rollout status deployment/wso2-api-manager -n customerx

### Escalation
If restart does not resolve within 10 minutes, escalate to Jane Smith (jane.smith@wso2.com).

---

## Incident: Pod memory usage above 90%

**Ticket reference:** SRE-1051
**Severity:** P2

### Diagnosis steps
1. Check current memory usage per pod:
   kubectl top pods -n customerx
2. Check if HPA is scaling:
   kubectl get hpa -n customerx
3. Check JVM heap usage inside pod:
   kubectl exec -it <pod-name> -n customerx -- jstat -gcutil 1 5

### Fix
If HPA is not auto-scaling, manually scale up:
  kubectl scale deployment/wso2-api-manager -n customerx --replicas=6

If a single pod is at memory limit and OOMKilled:
  kubectl delete pod <pod-name> -n customerx   # forces restart, AKS will reschedule

### Escalation
If memory keeps spiking after scaling, open a WSO2 support ticket (subscription ID: CX-2024-PRD-001).

---

## Incident: API Manager pods not starting (CrashLoopBackOff)

**Severity:** P1 (full outage)

### Diagnosis steps
1. Check pod status:
   kubectl get pods -n customerx
2. Check pod events:
   kubectl describe pod <pod-name> -n customerx
3. Check recent logs:
   kubectl logs <pod-name> -n customerx --previous

### Common causes and fixes
- Database connection failure: Verify Azure SQL firewall allows AKS subnet (10.1.0.0/16)
- Image pull error: Check Azure Container Registry credentials
- ConfigMap missing: kubectl get configmap -n customerx

### Escalation
P1 incidents: Call Jane Smith immediately. If unreachable, call Bob Lee.
Engage WSO2 support for product-level issues.

---

## Routine: Rolling restart procedure

Used for: applying config changes, clearing memory leaks, post-patching.

1. Announce in Slack #sre-alerts: "Starting rolling restart for CustomerX at HH:MM UTC"
2. Run the restart:
   kubectl rollout restart deployment/wso2-api-manager -n customerx
3. Watch progress:
   kubectl rollout status deployment/wso2-api-manager -n customerx
4. Verify pods are healthy:
   kubectl get pods -n customerx
5. Run smoke test — check Publisher portal responds:
   curl -sk https://customerx.wso2-sre.internal/publisher | grep -i "wso2"
6. Announce completion in Slack.

---

## Routine: Checking CustomerX cluster health

Run these commands to verify overall health:
  kubectl get nodes                              # all nodes Ready
  kubectl get pods -n customerx                  # all pods Running
  kubectl top nodes                              # CPU/memory within limits
  kubectl get hpa -n customerx                  # HPA status and replica count
  kubectl get events -n customerx --sort-by=.lastTimestamp | tail -20  # recent events
