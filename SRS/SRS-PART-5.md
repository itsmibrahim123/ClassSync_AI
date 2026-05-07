# SRS - ClassSync AI

## Part 5: System Architecture, Models & Workflows

**Version: 1.0**

---

# 9. System Architecture

ClassSync AI follows a modular, scalable, cloud-based SaaS architecture.

It consists of the following layers:

1. **Web UI (Frontend)**
2. **Backend API (FastAPI)**
3. **AI Agent Service**
4. **ClassSync Core Engine (Optimizer)**
5. **Database (PostgreSQL)**
6. **Cloud Storage (S3-Compatible)**
7. **LLM Cloud API (OpenAI / Gemini)**

---

# 9.1 High-Level Architecture Diagram

```
+--------------------------------------------------------------+
|                          Web UI (React/HTML)                 |
|    Uploads | Constraints | Timetable Viewer | AI Chat Panel   |
+---------------------------+----------------------------------+
|
v
+--------------------------------------------------------------+
|                     FastAPI Backend API                      |
| Auth | Upload | Constraints | Scheduler | Exports | AI Proxy |
+---------------------------+----------------------------------+
|
+--------------+--------------+
|                             |
v                             v
+----------------------------+   +------------------------------+
|   ClassSync Core Engine    |   |       AI Agent Service       |
| Optimization | Validation  |<->|  GPT-4.1/Gemini Tool-Calling |
| Constraints | I/O Handlers |   | Structured JSON Operations   |
+----------------------------+   +------------------------------+
|
v
+--------------------------------------------------------------+
|                    PostgreSQL Database                       |
+--------------------------------------------------------------+
|
v
+--------------------------------------------------------------+
|                 S3-Compatible File Storage                   |
+--------------------------------------------------------------+
```

---

# 10. Data Model & Database Schema

Below are the major entities and their attributes.

---

# 10.1 Entity Definitions

### **Institution**

```
institution_id (PK)
name
subscription_status
created_at
updated_at
```

### **User**

```
user_id (PK)
institution_id (FK)
email
password_hash
role (Admin/Coordinator/Viewer)
created_at
```

### **Dataset**

```
dataset_id (PK)
institution_id (FK)
file_type
file_path
uploaded_at
status (valid/invalid)
```

### **Course**

```
course_id (PK)
institution_id (FK)
course_code
course_name
teacher_id (FK)
duration_minutes
section
expected_students
```

### **Teacher**

```
teacher_id (PK)
institution_id (FK)
name
max_load_hours
availability_json
```

### **Room**

```
room_id (PK)
institution_id (FK)
name
capacity
room_type
```

### **ConstraintProfile**

```
constraints_id (PK)
institution_id (FK)
hard_constraints_json
soft_constraints_json
optional_constraints_json
last_modified
```

### **Timetable**

```
schedule_id (PK)
institution_id (FK)
generated_at
status
score
ai_summary
```

### **TimetableEntry**

```
entry_id (PK)
schedule_id (FK)
course_id (FK)
teacher_id (FK)
room_id (FK)
day_of_week
start_time
end_time
```

### **AIInteractionLog**

```
log_id (PK)
institution_id (FK)
user_input
agent_action
tool_called
timestamp
```

---

# 10.2 ER Diagram (Text-Based)

```
Institution 1 --- N User
Institution 1 --- N Dataset
Institution 1 --- N Course
Institution 1 --- N Teacher
Institution 1 --- N Room
Institution 1 --- N ConstraintProfile
Institution 1 --- N Timetable
Timetable 1 --- N TimetableEntry
Course 1 --- N TimetableEntry
Teacher 1 --- N TimetableEntry
Room 1 --- N TimetableEntry
Institution 1 --- N AIInteractionLog
```

---

# 11. System Workflows

This section describes the internal workflow of critical system operations.

---

## 11.1 Dataset Upload Workflow

```
User → Web UI → /datasets/upload
→ Validate structure
→ AI-assisted cleaning suggestions
→ Save file → S3 storage
→ Record dataset metadata → DB
UI updates dataset status
```

---

## 11.2 Constraint Configuration Workflow

```
User opens Constraints Panel
→ Backend fetches constraint profile
User modifies constraints OR AI proposes changes
User confirms edits
→ /constraints/update saves JSON profile
```

---

## 11.3 Timetable Generation Workflow

```
User clicks "Generate Timetable"
→ /schedule/ggenerate
→ Validate datasets
→ Load constraints
→ ClassSync Core:
   1) Enforce hard constraints
   2) Apply soft constraints scoring
   3) Apply optional constraints
   4) Multi-pass optimization
   5) Conflict resolution
→ Save schedule + entries
→ Generate exports
UI displays result
```

---

## 11.4 Export Workflow

```
User selects export format
→ /export/{format}
→ Generate file
→ Return download link
```

---

## 11.5 AI Agent Interaction Workflow

```
User → AI Chat Panel
↓
/agent/query
↓
LLM interprets request
↓
If action required:
   Create structured tool call
↓
Backend executes tool
↓
Return result to LLM
↓
LLM generates final message to user
```

---

## 11.6 What-If Scenario Workflow

```
User: "Avoid classes after 2pm on Thursday"
↓
AI interprets → JSON constraint update
↓
AI asks for confirmation
↓
User confirms
↓
Temporary constraint set created
↓
Run scheduler again
↓
Compare old vs new timetable
↓
AI summarizes improvements or regressions
```

---

# 12. Optimization Engine Specification

---

## 12.1 Stage 1 — Data Preparation

- Standardize course codes
- Validate timeslot availability
- Convert all datasets to internal structures
- Remove duplicates and invalid entries

---

## 12.2 Stage 2 — Hard Constraint Enforcement

Hard constraints **cannot** be violated:

- Teacher overlap prevention
- Room overlap prevention
- Section overlap prevention
- Slot duration compliance
- Timeslot validity after subdividing

---

## 12.3 Stage 3 — Soft Constraint Optimization

Soft rules are applied using weighted scoring:

- Reduce morning/late-night classes
- Minimize teacher gaps
- Improve schedule compactness
- Respect teacher preferences
- Prefer specific room types

---

## 12.4 Stage 4 — Optional Constraints

- Room capacity check
- Grouping labs
- Avoid specific buildings
- Friday scheduling restrictions

---

## 12.5 Stage 5 — Search Algorithm

- Heuristic + iterative refinement
- Must converge within time limit
- Multi-pass evaluation
- Conflict resolution loop
- AI-assisted final review

---

## 12.6 Finalization

- Store timetable in DB
- Create visual outputs (PNG)
- Produce exports (XLSX, CSV, PDF, ZIP)
- Generate AI summary

---

# 13. Constraint Definition Tables

---

## 13.1 Hard Constraints

| ID   | Description                                       |
| ---- | ------------------------------------------------- |
| HC-1 | Teacher cannot teach two classes at the same time |
| HC-2 | Room cannot host multiple classes simultaneously  |
| HC-3 | A section cannot attend overlapping classes       |
| HC-4 | Timeslots must be valid and subdividable          |
| HC-5 | Course duration must match slot duration          |

---

## 13.2 Soft Constraints

| ID   | Description                      |
| ---- | -------------------------------- |
| SC-1 | Reduce morning classes           |
| SC-2 | Reduce late classes              |
| SC-3 | Minimize teacher gaps            |
| SC-4 | Prefer specific room types       |
| SC-5 | Prefer compact student schedules |
| SC-6 | Respect teacher slot preferences |

---

## 13.3 Optional (Toggleable) Constraints

| ID   | Description                    |
| ---- | ------------------------------ |
| OC-1 | Room capacity check            |
| OC-2 | Avoid Friday afternoons        |
| OC-3 | Group labs in blocks           |
| OC-4 | Avoid certain buildings        |
| OC-5 | Prevent schedule fragmentation |

---

# 14. Deployment Architecture

---

## 14.1 SaaS Deployment Model

```
            +----------------------------+
            |       User Browsers        |
            +--------------+-------------+
                           |
                           v
              HTTPS Load Balancer (Cloud)
                           |
           +---------------+-----------------+
           |                                 |
           v                                 v
   FastAPI Backend Servers            AI Agent Service
   (Stateless Containers)            (LLM API Proxy Layer)
           |                                 |
           +---------------+-----------------+
                           |
                           v
             PostgreSQL Multi-Tenant Database
                           |
                           v
               S3-Compatible Cloud Storage
```

---

# 15. Logging, Monitoring & Error Tracking

### Required Tools:

- Structured application logs
- AI tool-call logs
- Performance metrics
- Error tracking (Sentry, etc.)
- Cloud provider monitoring dashboards

---

# 16. LMS Integration (Future)

Future versions shall support:

- Sync timetable to LMS (Canvas, Moodle, Blackboard)
- Export ICS calendar feeds
- Teacher/student LMS dashboards

---
