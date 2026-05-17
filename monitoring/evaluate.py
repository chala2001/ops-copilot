# monitoring/evaluate.py - RAG Evaluation with Complete Exception Handling

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy
    from datasets import Dataset
    from core.rag import ask
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    from core.config import GOOGLE_API_KEY, LLM_MODEL
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    print(f"❌ Missing required library: {e}")
    print("Install with: pip install ragas datasets langchain-google-genai")
    sys.exit(1)

if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY not set")
    print("❌ GOOGLE_API_KEY not set in config or .env file")
    sys.exit(1)

try:
    eval_llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0
    )
    logger.info("Evaluation LLM initialized")
except Exception as e:
    logger.error(f"Failed to initialize evaluation LLM: {e}")
    print(f"❌ Cannot initialize Gemini for evaluation: {e}")
    sys.exit(1)

try:
    eval_embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=GOOGLE_API_KEY
    )
    logger.info("Evaluation embeddings initialized")
except Exception as e:
    logger.error(f"Failed to initialize embeddings: {e}")
    print(f"❌ Cannot initialize embeddings: {e}")
    sys.exit(1)

EVAL_QUESTIONS = [
    'What version of WSO2 API Manager is CustomerX running?',
    'What AKS node pool type does CustomerX use?',
    'What are the escalation contacts for CustomerX?',
    'Are there any known issues for CustomerX?',
    'What Kubernetes version does CustomerX use?',
]

def run_evaluation():
    '''Run RAG evaluation with comprehensive error handling.'''
    try:
        print('Starting RAG evaluation...')
        print('This calls Gemini multiple times — may take a few minutes.')

        data = {
            'question': [],
            'answer': [],
            'contexts': [],
        }

        for i, q in enumerate(EVAL_QUESTIONS):
            try:
                print(f'[{i+1}/{len(EVAL_QUESTIONS)}] Evaluating: {q}')

                answer, sources = ask(q, ['CustomerX', 'General'])

                data['question'].append(q)
                data['answer'].append(answer if answer else "No answer generated")
                data['contexts'].append([s.get('content', '') for s in sources] if sources else ['No context'])

                if i < len(EVAL_QUESTIONS) - 1:
                    time.sleep(2)

            except Exception as q_error:
                logger.error(f"Error evaluating question '{q}': {q_error}")
                data['question'].append(q)
                data['answer'].append(f"Error: {str(q_error)}")
                data['contexts'].append(['Error retrieving context'])
                continue

        if not data['question']:
            logger.error("No data collected for evaluation")
            print("❌ No data collected. Evaluation aborted.")
            return

        try:
            print("\nCalculating RAGAS metrics...")
            dataset = Dataset.from_dict(data)

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

        except Exception as eval_error:
            logger.error(f"RAGAS evaluation failed: {eval_error}")
            print(f"❌ Evaluation failed: {eval_error}")
            print("This usually happens due to API rate limits or quota exhaustion.")
            return

        try:
            scores_df = results.to_pandas()
            faith_score = scores_df['faithfulness'].mean()
            rel_score = scores_df['answer_relevancy'].mean()

            output = {
                'timestamp': datetime.now().isoformat(),
                'provider': 'gemini',
                'model': LLM_MODEL,
                'num_questions': len(EVAL_QUESTIONS),
                'faithfulness': round(float(faith_score), 4),
                'answer_relevancy': round(float(rel_score), 4),
                'per_question': scores_df[[
                    'question', 'faithfulness', 'answer_relevancy'
                ]].to_dict(orient='records')
            }

            with open('evaluation_results.json', 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            print('\n✅ Results saved to evaluation_results.json')
            print('Open the Streamlit app and go to the Evaluation Dashboard.')

        except Exception as save_error:
            logger.error(f"Error saving results: {save_error}")
            print(f"⚠️  Evaluation completed but failed to save results: {save_error}")

    except KeyboardInterrupt:
        print("\n⚠️  Evaluation interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in evaluation: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
