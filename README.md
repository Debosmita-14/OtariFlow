# 🚀 OtariFlow

**OtariFlow** is an AI-powered workflow system built using **LangGraph** that intelligently routes user queries while optimizing cost, improving response quality, and maintaining enterprise-grade security.

The system analyzes every request, selects the most suitable LLM, applies safety guardrails, checks the available budget, uses semantic caching when possible, and provides detailed analytics for monitoring.

---

## ✨ Features

- 🤖 AI-powered chatbot interface
- 🧠 LangGraph workflow orchestration
- 🔀 Intelligent LLM routing
- 💰 Cost-aware model selection
- 📊 Complexity analysis
- ⚡ Semantic caching using FAISS
- 🛡️ Prompt safety & security guardrails
- ✅ Hallucination detection
- 📈 Analytics dashboard
- 📝 Execution timeline tracking
- 🧾 Token usage monitoring
- 💾 SQLite database integration
- 🔐 Enterprise-ready architecture

---

## 🏗️ Project Structure

```
OtariFlow
│
├── backend/          # Core business logic
├── frontend/         # User Interface
├── graph/            # LangGraph workflow
├── database/         # Database models and CRUD operations
├── cache/            # Semantic cache (FAISS)
├── run.py            # Application entry point
├── requirements.txt
└── README.md
```

---

## ⚙️ Tech Stack

- Python
- LangGraph
- LangChain
- SQLite
- FAISS
- HTML
- CSS
- JavaScript

---

## 📂 Core Modules

### Backend
- Model Routing
- Budget Management
- Security Guardrails
- Memory Management
- Hallucination Checker
- Confidence Scoring
- Analytics
- Enterprise Features
- Token Dashboard

### Graph
- Workflow Definition
- Nodes
- State Management

### Database
- CRUD Operations
- Database Models
- SQLite Integration

### Cache
- FAISS Semantic Cache

### Frontend
- Chat Interface
- Dashboard
- Analytics View

---

## 🚀 Installation

### Clone the repository

```bash
git clone https://github.com/yourusername/OtariFlow.git

cd OtariFlow/Agent/Langgraph
```

### Create Virtual Environment

```bash
python -m venv .venv
```

Activate it

Windows

```bash
.venv\Scripts\activate
```

Linux/Mac

```bash
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

Copy

```
.env.example
```

to

```
.env
```

and update your API keys.

---

## ▶️ Run the Project

```bash
python run.py
```

or

```
start.bat
```

---

## 📈 Workflow

```
User
   │
   ▼
Chatbot
   │
   ▼
Complexity Analysis
   │
   ▼
Safety Guardrails
   │
   ▼
Budget Check
   │
   ▼
Semantic Cache
   │
 Cache Hit?
  │        │
 Yes      No
 │         │
 ▼         ▼
Return   Model Router
            │
            ▼
        Best LLM
            │
            ▼
      Response Generation
            │
            ▼
 Analytics & Logging
            │
            ▼
          User
```

---

## 📊 Key Capabilities

- Dynamic LLM selection
- Reduced inference cost
- Faster responses through caching
- Secure prompt handling
- Enterprise logging
- Analytics dashboard
- Execution tracking
- Token monitoring

---

## 📌 Future Enhancements

- Multi-agent collaboration
- Vector database integration
- RAG support
- Authentication & user management
- Docker deployment
- Cloud deployment
- Streaming responses

---

## 👨‍💻 Author

**Debosmita Banerjee**

---

## 📄 License

This project is intended for educational and research purposes.
