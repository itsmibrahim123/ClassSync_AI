# **ClassSync AI - Intelligent University Timetabling System**

### *AI-Powered. Cloud-Optimized. Constraint-Driven.*

---

## Overview

**ClassSync AI** is a next-generation, AI-powered university scheduling system designed to generate **clash-free, optimized academic timetables** in seconds.

Traditional timetabling tools fail with large datasets (100+ courses/teachers). ClassSync AI solves this with:

* A high-performance **Python-based optimization engine**
* A modern cloud **SaaS web platform**
* A built-in conversational **AI Agent (GPT-4.1 / Gemini)** that can refine, explain, and modify timetables
* Multi-export output formats (XLSX, CSV, PNG, PDF, JSON, ZIP)

---

## Key Features

### **1. AI-Assisted Scheduling**

* Configure constraints using natural language
* Auto-fix dataset issues
* Explain why a class was scheduled in a specific slot
* Run “what-if” scenarios (e.g.,  *“move labs to Wednesday afternoons”* )
* AI can adjust hard & soft constraints with user confirmation

---

### **2. Lightning-Fast Optimization Engine**

* Generates full university timetables in **≤60 seconds**
* Handles:
  * 200+ courses
  * 80+ instructors
  * 60 rooms
* Supports flexible slot durations (60, 90, 120 minutes)

---

### **3. Comprehensive Constraint System**

Supports **hard, soft, and optional** constraints:

* No teacher/room/section clashes
* Load balancing
* Reduce morning/late-night classes
* Minimize teacher gaps
* Group labs
* Optional: room capacity, building preferences, Friday restrictions

---

### **4. Multi-Format Export**

Users can download timetables in:

* **XLSX** (section/teacher/room views)
* **CSV**
* **PNG** timetable visuals
* **PDF** reports
* **JSON** API output
* **ZIP** bundles

---

### **5. Secure Cloud Dashboard**

* Email/password authentication
* Institution-level data isolation
* Constraint UI with presets & reset-to-default
* Dataset upload with AI-assisted validation
* Real-time generation progress feedback

---

## System Architecture

```
+---------------------------------------------------+
|                    Web UI                         |
|      React / HTML / JS + AI Chat Panel            |
+------------------------+--------------------------+
                         |
                         v
+------------------------------------------------------------+
|                      FastAPI Backend                       |
| Auth | Uploads | Constraints | Scheduler | Exports | Agent |
+------------------------+-----------------------------------+
                         | 
      +------------------+------------------+
      |                                     |
      v                                     v
+-----------------------+        +--------------------------+
| ClassSync Core Engine | <----> |   AI Agent (GPT/Gemini) |
| Optimization | Rules  |        | Tool Calling + Reasoning |
+-----------------------+        +--------------------------+
                         |
                         v
+------------------------------------------------------------+
| Database (PostgreSQL) | File Storage (S3-compatible bucket) |
+------------------------------------------------------------+
```

---

## Project Structure (Proposed)

```
classsync-ai/
│
├── classsync_api/          # FastAPI backend
├── classsync_core/         # Optimization engine
├── classsync_agent/        # LLM agent (tool calling)
├── classsync_ui/           # Frontend (React/HTML)
│
├── data/                   # Templates & sample datasets
├── exports/                # Output files (generated)
├── docs/                   # SRS, diagrams, manuals
└── README.md
```

---

## Installation (Developer Version)

### **1. Clone the repository**

```bash
git clone https://github.com/<your-org>/classsync-ai.git
cd classsync-ai
```

### **2. Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### **3. Install dependencies**

```bash
pip install -r requirements.txt
```

### **4. Configure environment variables**

Create `.env` file:

```
OPENAI_API_KEY=your_key
GEMINI_API_KEY=your_key
DATABASE_URL=postgres://...
S3_BUCKET=...
```

---

## Running the System

### **Run Backend API**

```bash
uvicorn classsync_api.main:app --reload
```

### **Run AI Agent (if separate service)**

```bash
python classsync_agent/service.py
```

### **Run Frontend**

Depends on stack (e.g., React):

```bash
npm install
npm run dev
```

---

## AI Agent Capabilities

The AI Agent is powered by:

* **OpenAI GPT-4.1 / 4.1-mini (Primary)**
* **Gemini 2.0 Flash / Pro (Secondary)**

The agent can:

* Interpret natural language into constraints

* Modify hard/soft constraints with confirmation

* Detect and fix dataset inconsistencies

* Explain scheduling choices

* Run what-if scenarios

* Summarize timetable quality

---

## API Overview (High-Level)

### **Authentication**

```
POST /auth/login
POST /auth/register
```

### **Datasets**

```
POST /datasets/upload
GET  /datasets/status
```

### **Constraints**

```
GET  /constraints
POST /constraints/update
POST /constraints/reset
```

### **Scheduling**

```
POST /schedule/generate
GET  /schedule/result
POST /schedule/what-if
```

### **Agent**

```
POST /agent/query
POST /agent/tools/modify-constraints
POST /agent/tools/explain-slot
```

---

## Security

* HTTPS-only transport
* Passwords hashed (bcrypt/argon2)
* JWT-based session handling
* Institution-level data isolation
* Obfuscated backend algorithm modules

---

## Roadmap

### **v1.0 (MVP)**

* Upload datasets
* Configure constraints
* Generate timetable
* AI agent for basic instructions
* Multi-format exports
* SaaS login

### **v1.5**

* AI-driven conflict resolution
* What-if simulations
* Performance tuning

### **v2.0**

* LMS integration (Canvas, Moodle)
* Student/Teacher portals
* API for external systems

### **v3.0**

* Predictive scheduling (machine learning)
* Institution-level analytics dashboard

---

## License

Proprietary — all rights reserved.

Unauthorized distribution or reverse-engineering is strictly prohibited.

---

## Contributing

Contribution guidelines will be added after v1.0 release.

For now, please contact: **[saadmughal321@gmail.com](mailto:your-email@example.com)**

---

## Support

For issues or feature requests, use:

* GitHub Issues
* Support Email
* Feedback form (coming soon)

---
