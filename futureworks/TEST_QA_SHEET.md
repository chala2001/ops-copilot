# Manual Test Q&A Sheet — SRE Ops Copilot

## How to use this sheet

1. Re-ingest all documents first (Ingestion Log page → Re-ingest all files)
2. Go to the chat page
3. Ask each question exactly as written below
4. Compare the answer against the Expected Answer
5. Check the Sources section — it should cite the correct file

A good answer does NOT need to match word-for-word.
It just needs to contain the key facts listed in "Must contain".

---

## SECTION 1 — Version Questions

### Q1
**Ask:** What version of WSO2 API Manager is CustomerX running?
**Must contain:** 4.2.1
**Source should cite:** customerX_architecture.md
**Fail if:** Mentions 4.1.0 or 4.3.0 instead

---

### Q2
**Ask:** What version of WSO2 API Manager is CustomerY running?
**Must contain:** 4.1.0
**Source should cite:** customerY_architecture.md
**Fail if:** Mentions 4.2.1 or 4.3.0

---

### Q3
**Ask:** Which customer is running the newest version of WSO2 API Manager?
**Must contain:** CustomerZ, version 4.3.0
**Source should cite:** customerZ_architecture.md

---

### Q4
**Ask:** What Kubernetes version does CustomerY use?
**Must contain:** 1.27.5
**Source should cite:** customerY_architecture.md

---

### Q5
**Ask:** What Kubernetes version is CustomerZ running?
**Must contain:** 1.29.1
**Source should cite:** customerZ_architecture.md

---

## SECTION 2 — Infrastructure Questions

### Q6
**Ask:** What AKS node pool type does CustomerX use?
**Must contain:** Standard_D4s_v3
**Source should cite:** customerX_architecture.md

---

### Q7
**Ask:** What AKS node type does CustomerZ use?
**Must contain:** Standard_D8s_v3
**Source should cite:** customerZ_architecture.md

---

### Q8
**Ask:** Which region is CustomerY deployed in?
**Must contain:** West Europe
**Source should cite:** customerY_architecture.md

---

### Q9
**Ask:** What region is CustomerZ running in?
**Must contain:** Southeast Asia  (also acceptable: Singapore)
**Source should cite:** customerZ_architecture.md

---

### Q10
**Ask:** What database does CustomerZ use?
**Must contain:** Azure Cosmos DB
**Source should cite:** customerZ_architecture.md
**Fail if:** Says Azure SQL (that is CustomerX and CustomerY, not CustomerZ)

---

### Q11
**Ask:** What database server does CustomerX use?
**Must contain:** customerx-prod-sql.database.windows.net
**Source should cite:** customerX_architecture.md

---

### Q12
**Ask:** What is the maximum number of replicas CustomerX can scale to?
**Must contain:** 10
**Source should cite:** customerX_architecture.md or customerx-hpa.yaml

---

### Q13
**Ask:** What is the minimum number of gateway replicas for CustomerZ?
**Must contain:** 5
**Source should cite:** customerZ_architecture.md or customerz-hpa.yaml

---

### Q14
**Ask:** What memory limit is set for CustomerZ gateway pods?
**Must contain:** 8Gi
**Source should cite:** customerZ_architecture.md or customerz-deployment.yaml

---

### Q15
**Ask:** What CPU is requested for CustomerY pods?
**Must contain:** 500m
**Source should cite:** customerY_architecture.md or customery-deployment.yaml

---

## SECTION 3 — Known Issues and Workarounds

### Q16
**Ask:** What is the known issue SRE-1042 and how do I fix it?
**Must contain:**
- Throttling policy sync delay
- Restart the gateway pod
- kubectl rollout restart deployment/wso2-api-manager -n customerx
**Source should cite:** customerX_architecture.md or customerX_runbook.md

---

### Q17
**Ask:** CustomerX APIs are returning 429 errors even though quota is not exceeded. What should I do?
**Must contain:**
- SRE-1042 (or throttling policy sync)
- Restart the pod / rollout restart
**Source should cite:** customerX_runbook.md

---

### Q18
**Ask:** What is the known issue for CustomerY when subscription count is high?
**Must contain:**
- SRE-1067
- Slow API response / latency
- Subscription count exceeds 10,000
- Restart pods to flush subscription cache
**Source should cite:** customerY_architecture.md or customerY_runbook.md

---

### Q19
**Ask:** CustomerZ is getting RequestRateTooLargeException errors. What is the cause and fix?
**Must contain:**
- Cosmos DB connection pool exhaustion / SRE-1089
- Burst traffic above 5000 requests per second
- Increase Cosmos DB Request Units (RUs) to 50,000
**Source should cite:** customerZ_architecture.md or customerZ_runbook.md

---

### Q20
**Ask:** CustomerY TLS certificates are not renewing automatically. What should I check?
**Must contain:**
- SRE-1073
- kubectl get certificate -n customery
- Manually check on the 25th of each month
- Fewer than 10 days remaining → manual renewal
**Source should cite:** customerY_architecture.md or customerY_runbook.md

---

## SECTION 4 — Escalation Contacts

### Q21
**Ask:** Who is the primary escalation contact for CustomerX?
**Must contain:** Jane Smith, jane.smith@wso2.com
**Source should cite:** customerX_architecture.md

---

### Q22
**Ask:** Who should I call for a CustomerY P1 incident?
**Must contain:** Sarah Johnson, sarah.johnson@wso2.com
**Source should cite:** customerY_architecture.md or customerY_runbook.md

---

### Q23
**Ask:** Who are the escalation contacts for CustomerZ?
**Must contain:**
- Alex Wong, alex.wong@wso2.com (primary)
- Priya Nair, priya.nair@wso2.com (secondary)
**Source should cite:** customerZ_architecture.md

---

### Q24
**Ask:** What is CustomerZ's WSO2 support subscription ID?
**Must contain:** CZ-2025-PRD-003
**Source should cite:** customerZ_architecture.md

---

## SECTION 5 — SLA and Maintenance

### Q25
**Ask:** What is CustomerX's uptime SLA?
**Must contain:** 99.9%
**Source should cite:** customerX_architecture.md

---

### Q26
**Ask:** What is CustomerY's SLA uptime target?
**Must contain:** 99.5%
**Source should cite:** customerY_architecture.md

---

### Q27
**Ask:** Which customer has the strictest SLA?
**Must contain:** CustomerZ, 99.95%
**Source should cite:** customerZ_architecture.md

---

### Q28
**Ask:** What is CustomerX's maintenance window?
**Must contain:** Sunday, 02:00 AM to 04:00 AM UTC
**Source should cite:** customerX_architecture.md

---

### Q29
**Ask:** What is CustomerZ's RTO?
**Must contain:** 15 minutes
**Source should cite:** customerZ_architecture.md

---

### Q30
**Ask:** Does CustomerZ have any financial penalties for SLA breach?
**Must contain:** Yes / financial penalties / 30 minutes downtime
**Source should cite:** customerZ_architecture.md or customerZ_runbook.md

---

## SECTION 6 — Procedures

### Q31
**Ask:** How do I get AKS credentials for CustomerY's cluster?
**Must contain:**
- az aks get-credentials
- customery-prod-rg
- customery-aks-prod
**Source should cite:** general_sre_procedures.md

---

### Q32
**Ask:** How do I do a rolling restart for CustomerX?
**Must contain:**
- kubectl rollout restart deployment/wso2-api-manager -n customerx
- kubectl rollout status
**Source should cite:** customerX_runbook.md

---

### Q33
**Ask:** What is the P1 response time for on-call SREs?
**Must contain:** 5 minutes
**Source should cite:** general_sre_procedures.md

---

### Q34
**Ask:** How do I check memory usage for all CustomerZ pods?
**Must contain:** kubectl top pods -n customerz
**Source should cite:** customerZ_runbook.md or general_sre_procedures.md

---

## SECTION 7 — Cross-Customer Comparison Questions

### Q35
**Ask:** Compare the API Manager versions across all three customers.
**Must contain:**
- CustomerX: 4.2.1
- CustomerY: 4.1.0
- CustomerZ: 4.3.0
**Sources should cite:** multiple architecture files

---

### Q36
**Ask:** Which customer uses the largest node type in AKS?
**Must contain:** CustomerZ, Standard_D8s_v3
**Source should cite:** customerZ_architecture.md

---

### Q37
**Ask:** Which customer has the most aggressive autoscaling configuration?
**Good answer:** CustomerZ — can scale up to 20 gateway replicas, scale-up adds 3 at a time
**Source should cite:** customerZ_architecture.md or customerz-hpa.yaml

---

## SCORING GUIDE

| Score | Meaning |
|---|---|
| 34–37 correct | Excellent — RAG is working very well |
| 28–33 correct | Good — minor retrieval gaps, acceptable for production |
| 20–27 correct | Fair — check chunk size settings in config.py |
| Below 20 | Poor — re-check ingestion, verify all files were ingested |

## Common failure patterns to watch for

- **Wrong customer mix-up:** Model says CustomerX info when asked about CustomerY → embeddings too similar, increase TOP_K_RESULTS in config.py
- **No sources shown:** Sources section is empty → RAG found no matching chunks → check ingest ran successfully
- **Hallucination:** Answer contains facts not in any document → model is not grounding properly, check the system prompt in rag.py
- **Partial answers:** Gets some facts right but misses others → chunk size may be cutting off content, consider increasing CHUNK_SIZE in config.py
