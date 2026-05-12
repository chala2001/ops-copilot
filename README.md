# 🔍 WSO2 SRE Ops Copilot

**AI-Powered RAG Knowledge Base for Site Reliability Engineering Teams**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.31.0-red.svg)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Intelligent assistant that helps SRE teams quickly find deployment information, troubleshoot issues, and access runbooks using natural language queries powered by Google Gemini and RAG (Retrieval-Augmented Generation).

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Screenshots](#screenshots)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Document Management](#document-management)
- [Authentication](#authentication)
- [Deployment](#deployment)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

WSO2 SRE Ops Copilot is an intelligent knowledge base system designed specifically for Site Reliability Engineering teams. It uses Retrieval-Augmented Generation (RAG) to provide accurate, context-aware answers to questions about customer deployments, configurations, and operational procedures.

### Why This Tool?

**Traditional Problem:**
- SRE documentation scattered across multiple sources (Confluence, Git, PDFs, Slack)
- Finding specific deployment information takes 10-15 minutes
- Knowledge siloed with individual team members
- New team members spend weeks learning customer environments

**Our Solution:**
- ✅ **Instant Answers:** Ask questions in natural language, get answers in 2-3 seconds
- ✅ **Centralized Knowledge:** All deployment docs, runbooks, and configs in one place
- ✅ **Always Up-to-Date:** Automatic document ingestion keeps knowledge fresh
- ✅ **Source Citations:** Every answer includes source documents for verification
- ✅ **Team Collaboration:** Full access model - everyone can query all customer data

---

## ✨ Features

### 🤖 **AI-Powered Q&A**
- Natural language queries: "What version is CustomerX running?"
- Context-aware responses with source citations
- Streaming answers for real-time feedback
- Handles complex multi-step questions

### 📚 **Document Management**
- Supports Markdown, PDF, and YAML files
- Automatic document chunking and embedding
- MD5-based change detection (only re-ingests modified files)
- Scheduled auto-ingestion (configurable intervals)

### 🔐 **Authentication & Security**
- Session-based authentication with bcrypt password hashing
- Role-based access control (Admin, Senior SRE, SRE)
- Session timeout for security (configurable)
- Audit logging for all user activities

### 📊 **Analytics & Monitoring**
- **Evaluation Dashboard:** RAGAS metrics (faithfulness, relevancy)
- **Usage Dashboard:** Query analytics, user activity tracking
- **Ingestion Log:** Document status, MD5 checksums, change history
- **Query Logging:** Track all questions, answers, and latency

### 🔄 **Full Access Model**
- No customer segmentation (all SRE team members access all data)
- Simplified permissions (perfect for collaborative teams)
- Fast onboarding (new members immediately productive)

### 🐳 **Production-Ready**
- Docker & Docker Compose support
- Environment variable configuration
- Health checks and monitoring
- Backup & restore procedures
- Azure deployment guide

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web Interface                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   Chat   │  │Evaluation│  │Ingestion │  │  Usage   │  │
│  │  Page    │  │Dashboard │  │   Log    │  │Dashboard │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   RAG Engine (rag.py)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. User Question → Embed with sentence-transformers │  │
│  │  2. Search ChromaDB → Retrieve Top-K chunks          │  │
│  │  3. Build Context → Add retrieved docs to prompt     │  │
│  │  4. Call Gemini API → Generate answer                │  │
│  │  5. Stream Response → Return with source citations   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
│   ChromaDB   │  │Google Gemini │  │  Document Ingestion  │
│  (Vectors)   │  │   API (LLM)  │  │  - Markdown Loader   │
│              │  │              │  │  - PDF Loader        │
│              │  │              │  │  - YAML Loader       │
└──────────────┘  └──────────────┘  └──────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Streamlit | Web interface, chat UI |
| **LLM** | Google Gemini 1.5 Flash | Answer generation |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Text vectorization |
| **Vector DB** | ChromaDB | Semantic search |
| **Document Processing** | LangChain | Chunking, loading |
| **Evaluation** | RAGAS | Quality metrics |
| **Authentication** | bcrypt + Session State | Secure login |
| **Deployment** | Docker, Docker Compose | Containerization |

---

## 📸 Screenshots

### Chat Interface
Natural language Q&A with source citations and streaming responses.

```
┌─────────────────────────────────────────────────────────────┐
│ 🔍 SRE Ops Copilot                              Alice ✓     │
├─────────────────────────────────────────────────────────────┤
│ Total knowledge chunks: 3,247                               │
│ Access: All Customers                                       │
│                                                             │
│ Try asking:                                                 │
│ [What version is CustomerX running?                    ]   │
│ [What AKS node pool does CustomerX use?             ]   │
│ [Who are the escalation contacts for CustomerX?    ]   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ 👤 User: What version is CustomerX running?                │
│                                                             │
│ 🤖 Assistant: Based on the deployment configuration,        │
│    CustomerX is running WSO2 API Manager version 4.2.0.    │
│                                                             │
│    Sources: [customerx_deployment.md] [customerx.yaml]     │
│    View 2 source(s) ▼                                      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Ask about any customer deployment...                    [→]│
└─────────────────────────────────────────────────────────────┘
```

### Evaluation Dashboard
Track RAG system quality with faithfulness and relevancy metrics.

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 RAG Quality Dashboard                                    │
├─────────────────────────────────────────────────────────────┤
│ Last evaluated: 2026-05-12 14:30 | 5 questions             │
│                                                             │
│  Faithfulness        Answer Relevancy                      │
│     89.2%                 87.4%                            │
│  ✅ Above target      ✅ Above target                      │
│                                                             │
│ Per-Question Scores:                                        │
│ ┌──────────────────────────┬─────────┬────────────────┐   │
│ │ Question                 │ Faith.  │ Relevancy      │   │
│ ├──────────────────────────┼─────────┼────────────────┤   │
│ │ What version CustomerX?  │  95%   │     89%       │   │
│ │ What AKS node pool?      │  88%   │     84%       │   │
│ │ Escalation contacts?     │  91%   │     88%       │   │
│ └──────────────────────────┴─────────┴────────────────┘   │
│                                                             │
│ [🔄 Re-run evaluation now                               ]  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Docker (optional, for containerized deployment)
- Google Cloud account (for Gemini API key)
- 8GB RAM minimum (for local embedding model)

### 1. Clone Repository

```bash
git clone https://github.com/your-org/ops-copilot-gemini.git
cd ops-copilot-gemini
```

### 2. Setup Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Key

```bash
# Create .env file
cat > .env << 'EOF'
GOOGLE_API_KEY=your_google_api_key_here
LLM_MODEL=gemini-1.5-flash-latest
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_PATH=./chroma_db
EOF

# Get your API key from: https://aistudio.google.com/app/apikey
```

### 4. Add Documents

```bash
# Create data directories
mkdir -p data/markdown data/pdf data/yaml

# Add your documents
cp your_customer_docs.md data/markdown/
cp your_runbooks.pdf data/pdf/
cp your_deployments.yaml data/yaml/
```

### 5. Ingest Documents

```bash
# Run initial ingestion
python3 ingest.py

# Expected output:
# Loading embedding model...
# Loaded 10 markdown files
# Loaded 5 PDF files
# Loaded 3 YAML files
# Split 18 documents into 247 chunks
# ✅ Ingestion complete!
```

### 6. Run Application

```bash
# Start Streamlit
streamlit run app.py

# Application will open at: http://localhost:8501
```

### 7. Login

**Default credentials:**
- Username: `alice`
- Password: `password123`

⚠️ **Important:** Change default passwords before production deployment!

---

## 💻 Installation

### Option 1: Local Installation

**System Requirements:**
- Ubuntu 22.04 / macOS 12+ / Windows 10+ (with WSL2)
- Python 3.10+
- 8GB RAM minimum
- 10GB disk space

**Step-by-step:**

```bash
# 1. Clone repository
git clone https://github.com/your-org/ops-copilot-gemini.git
cd ops-copilot-gemini

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Setup configuration
cp .env.example .env
nano .env  # Add your GOOGLE_API_KEY

# 5. Initialize database
python3 ingest.py

# 6. Run application
streamlit run app.py
```

---

### Option 2: Docker Installation

**Prerequisites:**
- Docker 20.10+
- Docker Compose 2.0+

**Quick start:**

```bash
# 1. Clone repository
git clone https://github.com/your-org/ops-copilot-gemini.git
cd ops-copilot-gemini

# 2. Configure environment
cp .env.example .env
nano .env  # Add your GOOGLE_API_KEY

# 3. Build and start
docker compose up -d

# 4. Check logs
docker compose logs -f app

# 5. Access application
# Open browser: http://localhost:8501
```

**Docker services:**

```yaml
services:
  app:
    # Main Streamlit application
    # Port: 8501
    # Auto-restarts on failure
  
  scheduler:
    # Automatic document ingestion
    # Runs every 30 minutes
    # Checks for new/modified documents
```

---

### Option 3: Azure Deployment

For production deployment on Azure, see our comprehensive deployment guide:

📖 **[Azure Deployment Guide](docs/AZURE_DEPLOYMENT.md)** (Coming soon)

**Quick overview:**
- Virtual Machine: Standard_B2ms (2 vCPU, 8GB RAM)
- OS: Ubuntu 22.04 LTS
- Network: HTTPS with Nginx reverse proxy
- Estimated cost: ~$80-100/month
- Setup time: 2-3 hours

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# ── API Keys ──────────────────────────────────────────────
GOOGLE_API_KEY=your_google_api_key_here

# ── Model Configuration ────────────────────────────────────
LLM_MODEL=gemini-1.5-flash-latest
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ── Database ───────────────────────────────────────────────
CHROMA_PATH=./chroma_db
COLLECTION_NAME=sre_docs

# ── Document Processing ────────────────────────────────────
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5

# ── Data Directories ───────────────────────────────────────
MARKDOWN_DIR=./data/markdown
PDF_DIR=./data/pdf
YAML_DIR=./data/yaml

# ── Optional: Confluence Integration ───────────────────────
CONFLUENCE_URL=https://your-company.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your_confluence_token
CONFLUENCE_SPACE_KEY=SRE
```

### Configuration Files

#### `config.py`
Central configuration with environment variable loading and validation.

```python
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')  # Required
LLM_MODEL = os.getenv('LLM_MODEL', 'gemini-1.5-flash-latest')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '200'))
TOP_K_RESULTS = int(os.getenv('TOP_K_RESULTS', '5'))
```

#### `users.json`
User authentication database (bcrypt hashed passwords).

```json
{
  "users": {
    "alice": {
      "password_hash": "$2b$12$...",
      "display_name": "Alice (Senior SRE)",
      "customers": ["ALL"],
      "role": "senior_sre"
    }
  }
}
```

#### `docker-compose.yml`
Container orchestration configuration.

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    volumes:
      - ./data:/app/data
      - ./chroma_db:/app/chroma_db
    restart: unless-stopped
```

---

## 📖 Usage

### Basic Q&A

**Ask questions in natural language:**

```
Q: What version is CustomerX running?
A: CustomerX is running WSO2 API Manager version 4.2.0.

Q: How many replicas does CustomerY have?
A: CustomerY has 3 replicas configured in the deployment.

Q: Who is the escalation contact for CustomerX?
A: The escalation contact for CustomerX is Jane Smith (jane@wso2.com).

Q: What's the memory limit for CustomerX pods?
A: CustomerX pods have a memory limit of 4GB per pod.
```

### Advanced Queries

**Multi-step reasoning:**

```
Q: Compare CustomerX and CustomerY deployments
A: Here are the key differences:
   - CustomerX: 3 replicas, version 4.2.0, 4GB RAM
   - CustomerY: 2 replicas, version 4.1.0, 2GB RAM
   CustomerX has higher availability and newer version.
```

**Troubleshooting:**

```
Q: CustomerX pods keep restarting, what should I check?
A: Based on the runbook, pod restarts could indicate:
   1. OOM (Out of Memory) - Check if traffic >1000 req/s
   2. Health check failures - Verify readiness probe
   3. Resource constraints - Check CPU throttling
   
   First step: Check logs with: kubectl logs <pod-name>
```

### Using Dashboards

#### **Evaluation Dashboard**
Monitor RAG system quality:
1. Navigate to "Evaluation Dashboard" in sidebar
2. View faithfulness and relevancy scores
3. Check per-question breakdown
4. Click "Re-run evaluation" to refresh metrics

#### **Usage Dashboard**
Track system usage:
1. Navigate to "Usage Dashboard"
2. View query analytics by user
3. Check average latency
4. Monitor success rate

#### **Ingestion Log**
Manage documents:
1. Navigate to "Ingestion Log"
2. View tracked files with MD5 hashes
3. Click "Re-ingest all files" to update
4. Click "Clear database and re-ingest" for fresh start

---

## 📂 Document Management

### Supported File Types

| Type | Extensions | Use Case |
|------|-----------|----------|
| **Markdown** | `.md` | Runbooks, documentation, guides |
| **PDF** | `.pdf` | Technical manuals, architecture docs |
| **YAML** | `.yaml`, `.yml` | Kubernetes configs, deployment manifests |

### Document Structure

**Recommended folder structure:**

```
data/
├── markdown/
│   ├── customerx/
│   │   ├── deployment-guide.md
│   │   ├── runbook.md
│   │   └── troubleshooting.md
│   ├── customery/
│   │   └── deployment-guide.md
│   └── general/
│       └── best-practices.md
├── pdf/
│   ├── wso2-apim-manual.pdf
│   └── kubernetes-guide.pdf
└── yaml/
    ├── customerx/
    │   ├── deployment.yaml
    │   └── service.yaml
    └── customery/
        └── deployment.yaml
```

### Adding New Documents

**Method 1: Manual Upload**

```bash
# Copy files to data directory
cp new_document.md data/markdown/

# Re-run ingestion
python3 ingest.py
```

**Method 2: Via Dashboard**

1. Navigate to "Ingestion Log"
2. Add files to `data/` folders on server
3. Click "Re-ingest all files"
4. Wait for completion (progress shown in UI)

**Method 3: Automated (Scheduler)**

The scheduler automatically checks for new documents every 30 minutes:

```bash
# Start scheduler
python3 scheduler.py

# Or via Docker
docker compose up -d scheduler
```

### Best Practices

#### ✅ **DO:**

**Use clear, structured markdown:**

```markdown
# CustomerX Deployment

## Version Information
- **Product:** WSO2 API Manager
- **Version:** 4.2.0
- **Deployed:** 2024-01-15

## Infrastructure
- **Platform:** Kubernetes
- **Replicas:** 3
- **Resources:** 4GB RAM, 2 CPU

## Contacts
- **Primary:** John Doe (john@wso2.com)
- **Escalation:** Jane Smith (jane@wso2.com)
```

**Add metadata to YAML:**

```yaml
# customerx-deployment.yaml
# META: customer=CustomerX version=4.2.0 environment=production
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wso2-apim
...
```

#### ❌ **DON'T:**

- Use vague titles: ❌ "doc1.md" → ✅ "customerx-deployment-guide.md"
- Mix customers in one file: ❌ "all-customers.md"
- Use ambiguous abbreviations without explanation
- Forget to update docs after deployments

---

## 🔐 Authentication

### User Management

**Default users:**

| Username | Password | Role | Access |
|----------|----------|------|--------|
| `alice` | `password123` | Senior SRE | All customers |
| `bob` | `password` | SRE | All customers |
| `admin` | `admin` | Admin | All customers + Admin Panel |

⚠️ **Change these passwords before production use!**

### Adding New Users

**Method 1: Admin Panel (Recommended)**

1. Login as admin
2. Navigate to "Admin Panel"
3. Fill "Add New User" form:
   - Username: `john.doe`
   - Password: `SecurePassword123!`
   - Display Name: `John Doe (SRE)`
   - Role: `sre`
4. Click "Add User"

**Method 2: Python Script**

```python
# add_user.py
from auth import hash_password
import json

# Load users
with open('users.json', 'r') as f:
    data = json.load(f)

# Add new user
data['users']['john.doe'] = {
    'password_hash': hash_password('SecurePassword123!'),
    'display_name': 'John Doe (SRE)',
    'customers': ['ALL'],
    'role': 'sre'
}

# Save
with open('users.json', 'w') as f:
    json.dump(data, f, indent=2)

print("✅ User added successfully")
```

### Password Security

**Current implementation:**
- ✅ bcrypt hashing (industry standard)
- ✅ Automatic salt generation
- ✅ Cost factor 12 (4096 iterations)
- ✅ Session-based authentication
- ✅ 60-minute session timeout

**Password requirements:**
- Minimum 8 characters (recommended: 12+)
- Mix of uppercase, lowercase, numbers, symbols
- No common words or patterns

### Roles & Permissions

| Role | Permissions |
|------|------------|
| **sre** | Query knowledge base, view dashboards |
| **senior_sre** | Same as SRE (no functional difference currently) |
| **admin** | All of above + User management, system configuration |

---

## 🚀 Deployment

### Development Environment

```bash
# Start application locally
streamlit run app.py

# With live reload (auto-restart on file changes)
streamlit run app.py --server.runOnSave true

# On specific port
streamlit run app.py --server.port 8502

# With debug logging
streamlit run app.py --logger.level=debug
```

### Production Environment

#### **Using Docker Compose (Recommended)**

```bash
# 1. Configure production environment
cp .env.example .env
nano .env  # Set production values

# 2. Build and start services
docker compose -f docker-compose.prod.yml up -d

# 3. Check health
docker compose ps
docker compose logs -f app

# 4. Setup Nginx reverse proxy (optional)
sudo nano /etc/nginx/sites-available/sre-copilot
# See docs/nginx-config.md for configuration

# 5. Enable SSL/TLS
sudo certbot --nginx -d sre-copilot.your-domain.com
```

#### **Using Systemd (Linux)**

```bash
# 1. Create systemd service
sudo nano /etc/systemd/system/sre-copilot.service

# Add:
[Unit]
Description=WSO2 SRE Ops Copilot
After=network.target

[Service]
Type=simple
User=sreadmin
WorkingDirectory=/opt/ops-copilot
Environment="PATH=/opt/ops-copilot/venv/bin"
ExecStart=/opt/ops-copilot/venv/bin/streamlit run app.py
Restart=always

[Install]
WantedBy=multi-user.target

# 2. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable sre-copilot
sudo systemctl start sre-copilot

# 3. Check status
sudo systemctl status sre-copilot
```

### Cloud Deployment

**Azure Virtual Machine:**
- See [docs/AZURE_DEPLOYMENT.md](docs/AZURE_DEPLOYMENT.md)
- Estimated cost: $80-100/month
- Supports 20-50 concurrent users

**AWS EC2:**
- Instance: t3.medium (2 vCPU, 4GB RAM)
- OS: Ubuntu 22.04 LTS
- Estimated cost: $35-50/month

**Google Cloud (GCE):**
- Machine type: e2-standard-2 (2 vCPU, 8GB RAM)
- OS: Ubuntu 22.04 LTS
- Estimated cost: $50-70/month

---

## 📊 Monitoring & Logging

### Application Logs

**View logs:**

```bash
# Local deployment
streamlit run app.py 2>&1 | tee app.log

# Docker deployment
docker compose logs -f app
docker compose logs -f scheduler

# Systemd deployment
sudo journalctl -u sre-copilot -f
sudo journalctl -u sre-copilot -n 100
```

### Query Logs

**Location:** `query_log.json`

**Format:**
```json
{
  "queries": [
    {
      "timestamp": "2026-05-12T14:30:45",
      "username": "alice",
      "question": "What version is CustomerX running?",
      "customer_scope": ["ALL"],
      "answer_length": 85,
      "num_sources": 2,
      "latency_ms": 2340,
      "success": true,
      "top_source": "data/markdown/customerx_deployment.md"
    }
  ]
}
```

**Analyze logs:**

```python
# analyze_logs.py
import json
import pandas as pd

with open('query_log.json') as f:
    data = json.load(f)

df = pd.DataFrame(data['queries'])

print(f"Total queries: {len(df)}")
print(f"Average latency: {df['latency_ms'].mean():.0f}ms")
print(f"Success rate: {df['success'].mean():.1%}")
print(f"\nTop users:")
print(df['username'].value_counts())
```

### Evaluation Metrics

**Location:** `evaluation_results.json`

**Track over time:**

```bash
# Run evaluation
python3 evaluate.py

# Archive results
cp evaluation_results.json "results_$(date +%Y%m%d).json"

# Compare with previous
python3 compare_evaluations.py results_20260501.json results_20260512.json
```

### Health Checks

**Application health:**

```bash
# Check if app is responding
curl http://localhost:8501

# Check ChromaDB
python3 << 'EOF'
import chromadb
client = chromadb.PersistentClient(path='./chroma_db')
collection = client.get_collection('sre_docs')
print(f"✅ ChromaDB: {collection.count()} chunks")
EOF

# Check Gemini API
python3 << 'EOF'
from google import genai
from config import GOOGLE_API_KEY
client = genai.Client(api_key=GOOGLE_API_KEY)
response = client.models.generate_content(
    model='gemini-1.5-flash-latest',
    contents='Hello'
)
print(f"✅ Gemini API: {response.text[:50]}")
EOF
```

### Performance Monitoring

**Resource usage:**

```bash
# CPU and memory
htop

# Disk usage
df -h
du -sh chroma_db/
du -sh data/

# Network
netstat -tulpn | grep 8501
```

**Metrics to track:**
- Query latency (target: <3 seconds)
- Memory usage (target: <6GB)
- API rate limit hits (target: <5/day)
- Success rate (target: >95%)
- Evaluation scores (target: >85%)

---

## 🔧 Troubleshooting

### Common Issues

#### **Issue: "Cannot find GOOGLE_API_KEY"**

**Cause:** Environment variable not set

**Solution:**
```bash
# Check if .env exists
ls -la .env

# Verify content
cat .env | grep GOOGLE_API_KEY

# If missing, add it
echo "GOOGLE_API_KEY=your_key_here" >> .env

# Restart application
```

---

#### **Issue: "Rate limit exceeded (429)"**

**Cause:** Too many API requests

**Solution:**
```bash
# Option 1: Wait (free tier resets every minute)
# Option 2: Upgrade to paid tier
# Go to: https://console.cloud.google.com/billing

# Option 3: Add caching (reduces API calls)
# See docs/caching.md
```

---

#### **Issue: "Login not working"**

**Cause:** Incorrect password or corrupt users.json

**Solution:**
```bash
# Verify users.json exists
ls -la users.json

# Check format
python3 -c "import json; print(json.load(open('users.json')))"

# Reset to defaults
cp users.json.example users.json

# Or recreate with script
python3 migrate_passwords.py
```

---

#### **Issue: "No documents found"**

**Cause:** Documents not ingested or ChromaDB empty

**Solution:**
```bash
# Check if documents exist
ls -la data/markdown/
ls -la data/pdf/
ls -la data/yaml/

# Run ingestion
python3 ingest.py

# Verify ChromaDB has data
python3 -c "
import chromadb
client = chromadb.PersistentClient(path='./chroma_db')
coll = client.get_collection('sre_docs')
print(f'Chunks: {coll.count()}')
"
```

---

#### **Issue: "Session expired immediately"**

**Cause:** Session timeout too short or clock skew

**Solution:**
```bash
# Check session timeout setting
grep SESSION_TIMEOUT session_manager.py

# Increase timeout
nano session_manager.py
# Change: SESSION_TIMEOUT_MINUTES = 60

# Restart application
```

---

#### **Issue: "Docker container keeps restarting"**

**Cause:** Application crashing or port conflict

**Solution:**
```bash
# Check logs
docker compose logs app

# Check port availability
sudo netstat -tulpn | grep 8501

# Kill conflicting process
sudo pkill -f streamlit

# Restart containers
docker compose down
docker compose up -d
```

---

### Getting Help

**Resources:**
- 📖 [Full Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/your-org/ops-copilot-gemini/issues)
- 💬 [Discussions](https://github.com/your-org/ops-copilot-gemini/discussions)
- 📧 Email: sre-team@your-company.com

**Before opening an issue:**
1. Check existing issues
2. Include error logs
3. Specify Python, OS, and Docker versions
4. Describe steps to reproduce

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Development Setup

```bash
# 1. Fork repository
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/ops-copilot-gemini.git
cd ops-copilot-gemini

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install dev dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. Create feature branch
git checkout -b feature/your-feature-name

# 6. Make changes and test
python3 -m pytest tests/
python3 -m pylint *.py

# 7. Commit and push
git add .
git commit -m "Add: your feature description"
git push origin feature/your-feature-name

# 8. Open Pull Request
```

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings for functions
- Keep functions under 50 lines
- Write tests for new features

### Pull Request Process

1. Update README.md with details of changes
2. Update documentation if needed
3. Add tests for new functionality
4. Ensure all tests pass
5. Request review from maintainers

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 WSO2 SRE Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 🙏 Acknowledgments

**Technologies:**
- [Streamlit](https://streamlit.io) - Web interface framework
- [Google Gemini](https://ai.google.dev) - LLM for answer generation
- [ChromaDB](https://www.trychroma.com) - Vector database
- [LangChain](https://www.langchain.com) - Document processing
- [sentence-transformers](https://www.sbert.net) - Text embeddings
- [RAGAS](https://github.com/explodinggradients/ragas) - RAG evaluation

**Inspiration:**
- OpenAI's GPT-based assistants
- GitHub Copilot
- Internal SRE pain points at WSO2

**Contributors:**
- Chalaka Perera- Initial development


---

## 📮 Contact

**WSO2 SRE Team**
- 🌐 Website: TBC
- 📧 Email:TBC
- 💬 Slack: TBC
- 🐙 GitHub:TBC 

**Project Maintainers:**
- TBC
- TBC

---

## 🗺️ Roadmap

### ✅ **Completed (v1.0)**
- Core RAG functionality with Gemini
- Full-access authentication model
- Markdown, PDF, YAML support
- Docker deployment
- Evaluation dashboard
- Query logging
- Session management

### 🚧 **In Progress (v1.1)**
- [ ] Response caching for performance
- [ ] Advanced rate limiting
- [ ] Slack integration
- [ ] Multi-language support

### 📋 **Planned (v2.0)**
- [ ] Fine-tuned embeddings for WSO2 terminology
- [ ] Graph RAG for complex reasoning
- [ ] Voice input/output
- [ ] Mobile app
- [ ] Advanced analytics
- [ ] Automated runbook execution

### 💡 **Ideas (Future)**
- Integration with ticketing systems (Jira, ServiceNow)
- Predictive incident detection
- Automated documentation generation
- Multi-modal support (diagrams, screenshots)

**Want to help?** Check our [Contributing Guide](#contributing) and pick an issue tagged `good-first-issue`!

---

## ⭐ Star History

If this project helped you, consider giving it a star! ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=your-org/ops-copilot-gemini&type=Date)](https://star-history.com/#your-org/ops-copilot-gemini&Date)

---

## 📊 Project Statistics

![GitHub stars](https://img.shields.io/github/stars/your-org/ops-copilot-gemini?style=social)
![GitHub forks](https://img.shields.io/github/forks/your-org/ops-copilot-gemini?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/your-org/ops-copilot-gemini?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/your-org/ops-copilot-gemini)
![GitHub language count](https://img.shields.io/github/languages/count/your-org/ops-copilot-gemini)
![GitHub top language](https://img.shields.io/github/languages/top/your-org/ops-copilot-gemini)
![GitHub last commit](https://img.shields.io/github/last-commit/your-org/ops-copilot-gemini)

---

<div align="center">

**Made with ❤️ by the WSO2 SRE Team**

[⬆ Back to Top](#-wso2-sre-ops-copilot)

</div>
