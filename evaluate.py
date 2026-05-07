# evaluate.py
# Measures how good your RAG system is.
# Metrics:
#   - faithfulness: Did Gemini only use the provided context?
#   - answer_relevancy: Is the answer relevant to the question?

import os
import sys
import time
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset
from rag import ask
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from config import GOOGLE_API_KEY, LLM_MODEL

# ── Setup Gemini for Evaluation ─────────────────────────
# RAGAS needs an LLM and Embeddings to perform the evaluation
eval_llm = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    google_api_key=GOOGLE_API_KEY,
    temperature=0
)

eval_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GOOGLE_API_KEY
)

# ── Test questions for evaluation ───────────────────────
EVAL_QUESTIONS = [
    'What version of WSO2 API Manager is CustomerX running?',
    'What AKS node pool type does CustomerX use?',
    'What are the escalation contacts for CustomerX?',
    'Are there any known issues for CustomerX?',
    'What Kubernetes version does CustomerX use?',
]

def run_evaluation():
    print('Starting RAG evaluation...')
    print('This calls Gemini multiple times — may take a few minutes.')

    # Collect results for each question
    data = {
        'question': [],
        'answer': [],
        'contexts': [],
    }

    for q in EVAL_QUESTIONS:
        print(f'Evaluating: {q}')
        answer, sources = ask(q, ['CustomerX', 'General'])

        data['question'].append(q)
        data['answer'].append(answer)
        # contexts = list of retrieved chunk texts
        data['contexts'].append([s['content'] for s in sources])
        
        # Avoid rate limiting (429) on Gemini free tier
        time.sleep(2)

    # Run RAGAS evaluation
    dataset = Dataset.from_dict(data)
    
    # We pass both llm and embeddings to avoid OpenAI defaults
    results = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=eval_llm,
        embeddings=eval_embeddings
    )

    print('\n=== Evaluation Results ===')
    print(results)
    print('===========================')
    print('faithfulness: How much does Gemini stick to the retrieved context?')
    print('answer_relevancy: Is the answer relevant to the question?')
    print('Scores are 0.0 to 1.0. Target: > 0.8 for both.')

if __name__ == '__main__':
    run_evaluation()
