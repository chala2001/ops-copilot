# 08 — Evaluation: Measuring If the AI Is Any Good

> How do you know your RAG system is actually giving correct answers? This document explains RAGAS, the evaluation framework, and how to interpret the results.

---

## The Core Problem: AI Can Hallucinate

Google Gemini is a very powerful language model. But it can also confidently make things up — a phenomenon called **hallucination**. In a medical or legal context, hallucination is catastrophic. In an SRE context, it means an engineer might follow wrong runbook advice.

The RAG approach reduces hallucination by grounding answers in your documents. But we need to **measure** how well this grounding is working.

---

## What Is RAGAS?

RAGAS (Retrieval-Augmented Generation Assessment) is an open-source library specifically designed to evaluate RAG systems. It uses the same AI (Gemini) to judge the output of the RAG system.

This might seem circular: "use Gemini to check Gemini's work." But it's actually effective because the evaluation uses different prompts and a more structured analytical approach than the generation.

---

## The Two Metrics We Use

### Metric 1: Faithfulness

**Question it answers:** "Does the answer stick to what the documents say, or is Gemini inventing things?"

**How it's calculated:**
1. Take the answer Gemini produced
2. Break it into individual claims (e.g., "CustomerX runs version 4.2.0", "The cluster uses AKS")
3. For each claim, check if it's supported by the retrieved context
4. Score = (claims supported by context) / (total claims)

**Example:**
```
Context: "CustomerX runs WSO2 API Manager 4.2.0 on AKS Standard_D4s_v3 nodes."

Answer: "CustomerX runs WSO2 API Manager 4.2.0 on Azure Kubernetes Service.
         The cluster uses Standard_D4s_v3 nodes. Memory is 8GB per node."

Claims:
  ✅ "runs WSO2 API Manager 4.2.0"          → in context
  ✅ "Azure Kubernetes Service"              → in context (AKS = Azure Kubernetes Service)
  ✅ "Standard_D4s_v3 nodes"                → in context
  ❌ "Memory is 8GB per node"               → NOT in context → hallucination!

Faithfulness = 3/4 = 0.75 (75%)
```

**Target:** > 0.85 (85%)

**What a low score means:** Gemini is adding information not in your documents. This could be dangerous — an engineer might follow advice that isn't based on your actual deployment.

**How to fix:**
- Increase `TOP_K_RESULTS` in config.py (retrieve more context)
- Add more complete documents to your knowledge base
- Make the system prompt stricter: "Do NOT add any information not explicitly in the context"

---

### Metric 2: Answer Relevancy

**Question it answers:** "Does the answer actually address what was asked, or does it go off-topic?"

**How it's calculated:**
1. Take the answer
2. Use the AI to generate N "reverse questions" from the answer (questions that the answer would be the right response to)
3. Calculate the average similarity between the original question and the reverse questions
4. Higher similarity = answer is more on-topic

**Example:**
```
Question: "What version is CustomerX running?"

Answer: "CustomerX runs WSO2 API Manager 4.2.0. The cluster uses AKS with 
         Standard_D4s_v3 nodes and has 3 worker nodes in the production pool."

Reverse questions generated:
  "What software version is CustomerX using?" (very similar to original)
  "What infrastructure does CustomerX use?" (somewhat different)
  "How many nodes does CustomerX have?" (different topic)

Answer Relevancy = average similarity of reverse questions to original
                 = (0.95 + 0.72 + 0.51) / 3 = 0.73 (73%)
```

**Target:** > 0.80 (80%)

**What a low score means:** Answers include irrelevant information. Even if technically accurate, they're not answering what was asked.

**How to fix:**
- Improve the system prompt to focus answers: "Answer the specific question asked"
- Reduce `TOP_K_RESULTS` (too many chunks = AI picks tangential information)

---

## The Evaluation Questions

These 5 questions are used every time evaluation runs:

```python
EVAL_QUESTIONS = [
    'What version of WSO2 API Manager is CustomerX running?',
    'What AKS node pool type does CustomerX use?',
    'What are the escalation contacts for CustomerX?',
    'Are there any known issues for CustomerX?',
    'What Kubernetes version does CustomerX use?',
]
```

These are chosen to cover different types of information:
- Version information (specific numbers)
- Infrastructure configuration (specific technical details)
- People/contacts (directory information)
- Known issues (operational state)
- Platform versions (another specific number)

All answers should be findable in the `customerX_runbook.md` and `customerX_architecture.md` files.

---

## Running Evaluation

```bash
python evaluate.py
```

This takes 2-3 minutes because:
1. Each question goes through the full RAG pipeline (embed → search → Gemini)
2. RAGAS calls Gemini again for each answer to compute metrics
3. With 5 questions × 2 metrics × Gemini rate limits = ~10 API calls

After it finishes, results are saved to `evaluation_results.json`:

```json
{
  "timestamp": "2026-05-13T10:00:00",
  "provider": "gemini",
  "model": "gemini-flash-latest",
  "num_questions": 5,
  "faithfulness": 0.9200,
  "answer_relevancy": 0.8800,
  "per_question": [
    {
      "question": "What version of WSO2 API Manager is CustomerX running?",
      "faithfulness": 0.95,
      "answer_relevancy": 0.91
    },
    ...
  ]
}
```

---

## The Evaluation Pipeline (evaluate.py)

```python
# 1. Ask each question through the RAG system
for question in EVAL_QUESTIONS:
    answer, sources = ask(question, ['CustomerX', 'General'])
    data['question'].append(question)
    data['answer'].append(answer)
    data['contexts'].append([s['content'] for s in sources])  # the retrieved chunks

# 2. Build a RAGAS dataset
dataset = Dataset.from_dict(data)

# 3. Run RAGAS evaluation (calls Gemini internally)
results = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy],
    llm=eval_llm,           # Gemini for judging
    embeddings=eval_embeddings
)

# 4. Save results
output = {
    'faithfulness': results['faithfulness'].mean(),
    'answer_relevancy': results['answer_relevancy'].mean(),
    'per_question': [...]
}
with open('evaluation_results.json', 'w') as f:
    json.dump(output, f)
```

---

## How to Read the Evaluation Dashboard

The Evaluation Dashboard page reads `evaluation_results.json` and displays:

1. **Overall metrics** as big numbers with "Above target" / "Below target" labels
2. **Per-question table** with color coding (green/orange/red)
3. **Interpretation guide** (collapsible)
4. **Re-run button** to trigger a fresh evaluation

### Interpreting Color Codes

| Score Range | Color | Action Needed |
|-------------|-------|---------------|
| > 75% | Green | Good — no immediate action |
| 50–75% | Orange | Review — understand why |
| < 50% | Red | Problem — check documents and chunking |

### When to Run Evaluation

- After adding new documents (to confirm they improve coverage)
- After changing `CHUNK_SIZE` or `TOP_K_RESULTS` (to measure impact)
- On a weekly schedule (to detect regression)
- Before presenting to stakeholders (to have fresh numbers)

---

## Why Not Use Human Evaluation?

Human evaluation is the gold standard — a human reads each answer and judges it. But:

- It doesn't scale (147 daily queries × human review = full-time job)
- It's subjective (different engineers may disagree on answer quality)
- It can't be automated into a dashboard

RAGAS provides consistent, automated, scalable quality metrics. It's not perfect, but it catches regressions and gives you a trend line.

The best approach is both: use RAGAS for continuous automated monitoring, and do periodic human review of edge cases.
