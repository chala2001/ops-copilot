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
from datetime import datetime

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
    
    # ── Save results to JSON ──────────────────────────────
    scores_df = results.to_pandas()
    faith_score = scores_df['faithfulness'].mean()
    rel_score = scores_df['answer_relevancy'].mean()
    
    output = {
        'timestamp': datetime.now().isoformat(),
        'provider': 'gemini',
        'model': LLM_MODEL,
        'num_questions': len(EVAL_QUESTIONS),
        'faithfulness': round(faith_score, 4),
        'answer_relevancy': round(rel_score, 4),
        'per_question': scores_df[[
            'question', 'faithfulness', 'answer_relevancy'
        ]].to_dict(orient='records')
    }
    
    import json
    with open('evaluation_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print('\nResults saved to evaluation_results.json')
    print('Open the Streamlit app and go to the Evaluation tab.')

if __name__ == '__main__':
    from datetime import datetime
    run_evaluation()







# evaluate.py
# Measures how good your RAG system is.
# Metrics:
#   - faithfulness: Did Gemini only use the provided context?
#   - answer_relevancy: Is the answer relevant to the question?

# import os
# import sys
# import time
# import json
# from datetime import datetime
# from datasets import Dataset
# from rag import ask
# from config import GOOGLE_API_KEY, LLM_MODEL

# # RAGAS Imports
# from ragas import evaluate
# # Updated imports to avoid deprecation warnings
# from ragas.metrics import faithfulness, answer_relevancy
# from ragas.run_config import RunConfig
# from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# # ── Setup Gemini for Evaluation ─────────────────────────
# # RAGAS needs an LLM and Embeddings to perform the evaluation
# eval_llm = ChatGoogleGenerativeAI(
#     model=LLM_MODEL,
#     google_api_key=GOOGLE_API_KEY,
#     temperature=0
# )

# eval_embeddings = GoogleGenerativeAIEmbeddings(
#     model="models/embedding-001",
#     google_api_key=GOOGLE_API_KEY
# )

# # ── Test questions for evaluation ───────────────────────
# EVAL_QUESTIONS = [
#     'What version of WSO2 API Manager is CustomerX running?',
#     'What AKS node pool type does CustomerX use?',
#     'What are the escalation contacts for CustomerX?',
#     'Are there any known issues for CustomerX?',
#     'What Kubernetes version does CustomerX use?',
# ]

# def run_evaluation():
#     print('Starting RAG evaluation...')
#     print('NOTE: Using Gemini Free Tier. Adding delays to avoid 429 errors.')
#     print('This process will take ~2-3 minutes due to rate limiting.')

#     # Collect results for each question
#     data = {
#         'question': [],
#         'answer': [],
#         'contexts': [],
#     }

#     for i, q in enumerate(EVAL_QUESTIONS):
#         print(f'[{i+1}/{len(EVAL_QUESTIONS)}] Evaluating: {q}')
#         try:
#             answer, sources = ask(q, ['CustomerX', 'General'])

#             data['question'].append(q)
#             data['answer'].append(answer)
#             # contexts = list of retrieved chunk texts
#             data['contexts'].append([s['content'] for s in sources])
            
#             # CRITICAL: Sleep 10s between questions to avoid hitting RPM limit
#             # The free tier is roughly 15 requests per minute.
#             if i < len(EVAL_QUESTIONS) - 1:
#                 print("Waiting 10s to stay within rate limits...")
#                 time.sleep(10)

#         except Exception as e:
#             print(f"Error during 'ask' for question '{q}': {e}")
#             continue

#     if not data['question']:
#         print("No data collected. Evaluation aborted.")
#         return

#     # Run RAGAS evaluation
#     print("\nCalculating RAGAS metrics (Faithfulness & Relevancy)...")
#     dataset = Dataset.from_dict(data)
    
#     # Configure RAGAS to be more patient with the Gemini API
#     run_config = RunConfig(
#         timeout=60, 
#         max_retries=10, 
#         max_wait=60
#     )

#     try:
#         # We pass both llm and embeddings to avoid OpenAI defaults
#         results = evaluate(
#             dataset=dataset,
#             metrics=[faithfulness, answer_relevancy],
#             llm=eval_llm,
#             embeddings=eval_embeddings,
#             run_config=run_config
#         )

#         print('\n=== Evaluation Results ===')
#         print(results)
#         print('===========================')
        
#         # ── Save results to JSON ──────────────────────────────
#         scores_df = results.to_pandas()
#         faith_score = scores_df['faithfulness'].mean()
#         rel_score = scores_df['answer_relevancy'].mean()
        
#         output = {
#             'timestamp': datetime.now().isoformat(),
#             'provider': 'gemini',
#             'model': LLM_MODEL,
#             'num_questions': len(EVAL_QUESTIONS),
#             'faithfulness': round(faith_score, 4),
#             'answer_relevancy': round(rel_score, 4),
#             'per_question': scores_df[[
#                 'question', 'faithfulness', 'answer_relevancy'
#             ]].to_dict(orient='records')
#         }
        
#         with open('evaluation_results.json', 'w') as f:
#             json.dump(output, f, indent=2)
        
#         print('\nResults saved to evaluation_results.json')
#         print('Open the Streamlit app and go to the Evaluation tab.')

#     except Exception as e:
#         print(f"Error during RAGAS evaluation: {e}")
#         print("This usually happens if the Gemini daily quota is completely exhausted.")

# if __name__ == '__main__':
#     run_evaluation()
