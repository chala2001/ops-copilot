# Project 4: AI-Powered Ops Knowledge Base (RAG-based CMDB)

## Description

The WSO2 SRE team manages deployments for a large number of customers across multiple cloud environments. Details about each customer's deployment, including architecture, component versions, configuration specifics, known issues, and escalation contacts, are currently scattered across internal wikis, runbooks, Confluence pages, and team members' institutional knowledge.

This project aims to build a Retrieval-Augmented Generation (RAG) system that serves as a centralised, queryable knowledge base for all customer deployment information. This is a well-established pattern in the industry, sometimes referred to as an AI-powered CMDB (Configuration Management Database) or an Internal Ops Copilot. Real-world examples include Uber's internal "Genie" system, which uses the same RAG architecture to serve internal knowledge queries via Slack.

Engineers should be able to ask natural language questions such as: "What version of WSO2 API Manager is Customer X running?" or "What AKS node pool configuration does Customer Y use?" and receive accurate, sourced answers, reducing time spent searching for deployment context during incidents and onboarding.

Key capabilities include:

- Ingestion of deployment documentation from multiple sources (Confluence, Markdown files, GitHub)
- Semantic search over ingested content using vector embeddings
- Natural language Q&A interface grounded in retrieved deployment context
- Source attribution so engineers know where an answer originated
- Access control, ensuring sensitive customer data is only visible to authorised team members

---

## Scope

The scope of this project includes:

- Design of a document ingestion pipeline supporting multiple source formats (Confluence, Markdown, PDF)
- Chunking, embedding, and storage of documents in a vector database (e.g., ChromaDB, Qdrant, or Azure AI Search)
- Integration with an LLM (Claude or equivalent) for answer generation over retrieved context
- A simple chat-style web interface for querying the knowledge base
- Access control considerations for sensitive customer deployment data
- Evaluation framework to measure retrieval quality and answer accuracy

---

## Learning Material

- [LangChain documentation](https://docs.langchain.com/)
- [LlamaIndex documentation](https://docs.llamaindex.ai/)
- [ChromaDB](https://docs.trychroma.com/)
- [Azure AI Search](https://learn.microsoft.com/en-us/azure/search/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [RAG foundational paper](https://arxiv.org/abs/2005.11401)

---

## Skills

- Natural language processing and LLM concepts
- Vector search and embeddings
- Data ingestion pipeline design
- Web application development

---

## Languages / Technologies

- **Python** — ingestion pipeline, RAG backend
- **LangChain or LlamaIndex** — RAG orchestration
- **ChromaDB, Qdrant, or Azure AI Search** — vector store
- **Claude API or OpenAI** — LLM layer
- **React or Streamlit** — frontend interface
- `.md` and `.yaml` as inputs
- Tfstate and config files sync
