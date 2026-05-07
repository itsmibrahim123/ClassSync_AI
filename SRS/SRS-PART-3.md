# SRS - ClassSync AI

## Part 3: External Interface Requirements

Version: 1.0

---

# 7. External Interface Requirements

This section defines all user-facing and system-facing interfaces, including UI design expectations, backend API behavior, AI Agent interactions, software/hardware interfaces, and communication protocols.

---

# 7.1 User Interface (UI) Requirements

## 7.1.1 General UI Requirements

The system shall provide a modern, responsive, browser-based interface with:

- Clean dashboard-style layout
- Accessible navigation menu
- AI chat panel available on all main screens
- Error and confirmation messages clearly visible
- Tooltips and contextual help from the AI agent
- Loading indicators for actions with >500ms execution time

Supported browsers:

- Google Chrome
- Microsoft Edge
- Mozilla Firefox

---

## 7.1.2 Required Screens

### **7.1.2.1 Login Screen**

- Email + password fields
- “Forgot Password” option
- Redirect to Dashboard upon successful login

### **7.1.2.2 Dashboard Home**

Displays system at-a-glance information:

- Dataset upload status
- Number of teachers/courses/rooms
- Last timetable generation date
- Quick actions
- AI suggestion banner

### **7.1.2.3 Dataset Upload Screen**

Functionality:

- Upload CSV/XLSX for courses, teachers, rooms, sections
- Drag-and-drop support
- Field mapping preview
- AI-assisted validation messages
- Submission history

### **7.1.2.4 Constraints Configuration Screen**

Components:

- Sections for hard, soft, and optional constraints
- Toggles, sliders, and input fields
- Subdividable timeslot configuration
- AI-recommended constraints area
- Reset to Default button
- Save & Apply button

### **7.1.2.5 Timetable Generation Screen**

Features:

- “Generate Timetable” button
- Real-time logs (optional via WebSocket)
- Visual progress bar
- Estimated time remaining
- AI commentary panel

### **7.1.2.6 Timetable Viewer Screen**

Views:

- By Section
- By Teacher
- By Room

Capabilities:

- Color-coded grid
- Click-to-inspect class details
- AI explanation button
- Filters for day, room, teacher
- Zoom control
- Conflict highlighting

### **7.1.2.7 Export Screen**

User can choose:

- XLSX
- CSV
- PNG
- PDF
- ZIP (all combined)

### **7.1.2.8 AI Agent Chat Panel**

Functions:

- Natural-language conversation
- Quick reply options
- Export JSON previews
- AI-generated summaries
- “Apply Suggestion” button

### **7.1.2.9 User Settings**

- Change password
- AI autonomy level control
- Notification preferences

---

# 7.2 API Requirements

All backend services are exposed using **FastAPI** REST endpoints.

## 7.2.1 General API Constraints

- All endpoints must require authentication
- All responses in JSON format
- Must follow REST standard conventions
- Must include OpenAPI/Swagger documentation
- Validation errors must be explicit and descriptive

---

## 7.2.2 Authentication APIs

### **POST /auth/login**

- Authenticate user
- Returns JWT token

### **POST /auth/register**

- Register institution admin
- Sends verification email (optional future)

### **POST /auth/reset-password**

- Generates password reset link or token

---

## 7.2.3 Dataset APIs

### **POST /datasets/upload**

- Accepts CSV/XLSX
- Performs validation
- Returns file status

### **GET /datasets/status**

- Returns completeness and validation state

### **DELETE /datasets/reset**

- Deletes all institution datasets

---

## 7.2.4 Constraint APIs

### **GET /constraints**

- Returns current constraint profile

### **POST /constraints/update**

- Updates constraint JSON

### **POST /constraints/reset**

- Restores system default constraint configuration

---

## 7.2.5 Scheduler APIs

### **POST /schedule/generate**

- Initiates timetable generation
- Returns process ID

### **GET /schedule/status**

- Polls generation progress

### **GET /schedule/result**

- Returns final schedule data

### **POST /schedule/what-if**

- Generates alternative schedule based on temporary constraints

---

## 7.2.6 Export APIs

### **GET /export/xlsx**

### **GET /export/csv**

### **GET /export/png**

### **GET /export/pdf**

### **GET /export/zip**

All return downloadable files or file URLs.

---

# 7.3 AI Agent Interaction Requirements

## 7.3.1 LLM Model Requirements

Primary LLM: **OpenAI GPT-4.1 / 4.1-mini**
Secondary LLM: **Gemini 2.0 Flash/Pro**

Both accessed through cloud APIs.

---

## 7.3.2 Interaction Workflow

1. User submits natural-language query
2. Query is sent to `/agent/query`
3. LLM interprets using structured tool-calling
4. If backend action is required:
   - LLM generates structured “function call” JSON
   - Backend executes tool
   - Returns result to LLM
5. LLM composes final response to user

---

## 7.3.3 Required AI Agent Tools

| Tool Name               | Description                                     |
| ----------------------- | ----------------------------------------------- |
| `validate_data`       | Check datasets for issues                       |
| `fix_dataset_issues`  | Auto-correct or recommend fixes                 |
| `update_constraint`   | Modify hard/soft/optional constraints           |
| `reset_constraints`   | Restore defaults                                |
| `run_scheduler`       | Trigger timetable generation                    |
| `simulate_scenario`   | Run what-if timetable                           |
| `explain_slot`        | Explain why class is scheduled at specific time |
| `summarize_timetable` | Provide AI-generated summary                    |

---

## 7.3.4 AI Safety Requirements

- AI must always request confirmation before modifying constraints
- AI cannot override hard constraints unless explicitly allowed
- AI must log:
  - Input
  - Tool call
  - Output
- Misleading or hallucinated data is prohibited

---

# 7.4 Software Interfaces

### Backend Libraries:

- FastAPI
- Pydantic
- Pandas
- NumPy
- OpenPyXL
- ReportLab
- Matplotlib

### AI Libraries:

- `openai` Python SDK
- `google-generativeai` Python SDK
- LangChain (optional intermediary)

### Cloud Interfaces:

- PostgreSQL database
- S3-compatible storage
- SMTP/email provider

---

# 7.5 Hardware Interfaces

Since ClassSync AI is SaaS:

- Only requirement is a modern computer with internet access
- Backend hosted on cloud servers with auto-scaling

---

# 7.6 Communication Interfaces

- All traffic over **HTTPS/TLS 1.2+**
- JSON as standard messaging format
- AI Agent may use:
  - REST
  - Streaming responses (optional)
- WebSockets may be used for real-time generation logs

---
