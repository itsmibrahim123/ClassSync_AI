# Software Requirements Specification (SRS) - ClassSync AI

**Version:** 1.0  
**Generated Date:** 2024-12-30  
**Source:** Extracted from Project Documentation, Architecture Diagrams, and Use Case Models.

---

## 1. Introduction

### 1.1 Purpose
The purpose of this document is to define the comprehensive software requirements for **ClassSync AI**, a cloud-based University Timetabling System. These requirements are derived directly from the system's architectural blueprints, sequence diagrams, and use case definitions. This document serves as the authoritative baseline for development, testing, and validation of the system.

### 1.2 Scope
ClassSync AI is a SaaS platform designed to automate university course scheduling. It utilizes a genetic algorithm to generate conflict-free timetables and integrates a Large Language Model (LLM) agent to facilitate natural language configuration and analysis. The system encompasses a React-based web frontend, a FastAPI backend, a Python-based optimization engine, and cloud-based storage and database services.

### 1.3 Definitions and Acronyms
*   **GA:** Genetic Algorithm.
*   **Hard Constraint:** A mandatory rule that cannot be violated (e.g., physical resource clashes).
*   **Soft Constraint:** A preference rule that should be optimized but can be violated with a penalty.
*   **SaaS:** Software as a Service.
*   **LLM:** Large Language Model.
*   **RBAC:** Role-Based Access Control.
*   **JWT:** JSON Web Token.

---

## 2. Functional Requirements

Functional requirements describe the specific behaviors, functions, and interactions the system must support, primarily derived from `@SRS/USE-CASE.md` and `@SRS/SEQUENCE.md`.

### 2.1 Authentication & User Management
*   **FR-AUTH-01:** The system shall allow University Administrators to log in securely using an email and password.
*   **FR-AUTH-02:** The system shall issue a JSON Web Token (JWT) upon successful authentication to manage the user session.
*   **FR-AUTH-03:** The system shall support Role-Based Access Control (RBAC), distinguishing between roles such as Admin (full access), Coordinator, and Viewer.
*   **FR-AUTH-04:** The system shall enforce multi-tenancy, ensuring that data is logically isolated per institution.

### 2.2 Data Management
*   **FR-DATA-01:** The system shall provide an interface for users to upload academic datasets in CSV and XLSX formats.
    *   **FR-DATA-01.1:** Required datasets include **Courses** (Code, Name, Duration), **Teachers** (Name, Availability), **Rooms** (Capacity, Type), and **Student Sections** (Size).
*   **FR-DATA-02:** The system shall automatically validate uploaded datasets immediately upon receipt for schema compliance, duplicate entries, and missing mandatory fields.
*   **FR-DATA-03:** The system shall store validated raw dataset files in S3-compatible cloud storage.
*   **FR-DATA-04:** The system shall allow the AI Assistant to assist in validating data and suggesting fixes for logical inconsistencies.

### 2.3 Constraint Configuration
*   **FR-CONF-01:** The system shall allow users to configure **Hard Constraints** (e.g., "No double booking") and **Soft Constraints** (e.g., "Minimize gaps").
*   **FR-CONF-02:** The system shall allow users to toggle **Optional Constraints** (e.g., "Enforce room capacity").
*   **FR-CONF-03:** The system shall support the configuration of timeslot preferences and durations (60, 90, 120 minutes).
*   **FR-CONF-04:** The system shall interpret natural language commands via the AI Agent to modify constraints (e.g., "Don't schedule labs on Fridays") into structured system rules.
    *   **Traceability:** `@SRS/SEQUENCE.md` (AI-Assisted Configuration Workflow).

### 2.4 Timetable Generation (Optimization Engine)
*   **FR-SCHED-01:** The system shall generate a conflict-free timetable using a Genetic Algorithm (GA) optimization engine.
*   **FR-SCHED-02:** The generation process shall be triggered via the API (`POST /schedule/generate`), which fetches active datasets and constraints from the database.
*   **FR-SCHED-03:** The engine shall prioritize Hard Constraints; a schedule with Hard Constraint violations must have a fitness score of 0 (invalid).
*   **FR-SCHED-04:** The engine shall optimize the schedule based on a weighted sum of Soft Constraint satisfaction.
*   **FR-SCHED-05:** The system shall persist the "Best Schedule" found to the database as `TimetableEntry` records upon completion.
    *   **Traceability:** `@SRS/SEQUENCE.md` (Timetable Generation Workflow).

### 2.5 AI Agent & Assistant
*   **FR-AI-01:** The AI Agent shall operate as a distinct actor capable of interpreting natural language queries and mapping them to backend tool calls (`update_constraint`, `explain_slot`, `simulate_scenario`).
*   **FR-AI-02:** **Confirmation Loop:** The AI Agent must explicitly request and receive user confirmation before applying any changes to constraints or triggering a new schedule generation.
*   **FR-AI-03:** The system shall allow users to run "What-If" scenarios where the AI creates a temporary constraint set to simulate schedule changes without affecting the master schedule.
*   **FR-AI-04:** The AI Agent shall provide explanations for scheduling decisions (e.g., "Why is Course A at 9 AM?") by analyzing resource availability and constraints.

### 2.6 Export & Visualization
*   **FR-EXP-01:** The system shall provide interactive timetable views filtered by **Student Section**, **Teacher**, and **Physical Room**.
*   **FR-EXP-02:** The system shall allow users to export the final timetable in the following formats: **XLSX**, **CSV**, **PDF**, **PNG**, and **JSON**.

---

## 3. Data Requirements

Data requirements define the entities, attributes, and relationships required for system operation, derived primarily from `@SRS/SIMPLE-CLASS-DIAGRAM.md` and `@SRS/SRS-PART-5.md`.

### 3.1 Data Entities
*   **Institution:** Represents the tenant/university.
*   **User:** Represents an authenticated actor with a role.
*   **Course:** Attributes: Code, Name, Credit Hours, Duration (Minutes).
*   **Teacher:** Attributes: Name, Email, Preferred Times (Availability).
*   **Room:** Attributes: Room Number, Capacity, Is Lab (Boolean), Type.
*   **StudentSection:** Attributes: Section Name, Number of Students.
*   **Constraint:** Attributes: Description, Type (Hard/Soft), Priority Weight.
*   **Timetable:** Attributes: Semester, Generated Date, Quality Score (Fitness).
*   **ScheduledSession:** Attributes: Day of Week, Start Time, End Time.

### 3.2 Data Relationships
*   **User to AI Agent:** 1:1 Interaction session.
*   **Timetable to ScheduledSession:** A Timetable contains many (`*`) Scheduled Sessions.
*   **ScheduledSession Relationships:**
    *   Must be linked to exactly one **Course**.
    *   Must be linked to exactly one **Teacher**.
    *   Must be linked to exactly one **Room**.
    *   Must be linked to exactly one **StudentSection**.
*   **SchedulingEngine Dependencies:** The engine reads Courses, Teachers, and Rooms; and enforces Constraints.

### 3.3 Data Storage & Constraints
*   **Storage:** Raw datasets are stored in S3-compatible storage. Structured relational data is stored in PostgreSQL.
*   **Validation:** Datasets must adhere to defined schemas (e.g., numerical capacity, valid email formats).

---

## 4. Non-Functional Requirements

Non-functional requirements describe quality attributes, constraints, and operational standards.

### 4.1 Performance
*   **NFR-PERF-01:** The optimization engine shall generate a feasible schedule for a standard dataset (200 courses, 80 teachers, 60 rooms) in **≤ 60 seconds**.
*   **NFR-PERF-02:** Dashboard screens and standard UI interactions shall load in **≤ 2 seconds**.
*   **NFR-PERF-03:** The AI Agent shall return responses to standard queries within **2 to 5 seconds**.

### 4.2 Security & Privacy
*   **NFR-SEC-01:** All data in transit must be encrypted using **HTTPS/TLS 1.2+**.
*   **NFR-SEC-02:** User passwords must be salted and hashed using strong algorithms (e.g., **bcrypt** or **Argon2**).
*   **NFR-SEC-03:** Institution data must be logically isolated (Multi-tenancy). A user from one institution must strictly not access data from another.
*   **NFR-SEC-04:** Proprietary algorithmic modules (core optimization logic) shall be obfuscated to protect intellectual property.
*   **NFR-SEC-05:** Institution data shall **not** be used to train public LLM models.

### 4.3 Reliability & Availability
*   **NFR-REL-01:** The SaaS platform shall target a monthly availability (uptime) of **99.5%**.
*   **NFR-REL-02:** The system shall implement an **Auto-Save** feature for user configurations (constraints) to prevent data loss.
*   **NFR-REL-03:** Failed optimization runs must not corrupt existing data and must provide actionable error messages.

### 4.4 Usability
*   **NFR-USE-01:** The web interface shall be responsive and compatible with modern browsers (Chrome, Edge, Firefox).
*   **NFR-USE-02:** Error messages and AI explanations must be presented in plain, non-technical language suitable for academic administrators.

### 4.5 Maintainability & Architecture
*   **NFR-ARCH-01:** The system shall follow a modular architecture with strict separation between the Frontend (React), Backend API (FastAPI), Core Engine (Python), and AI Service.
*   **NFR-ARCH-02:** The backend shall support horizontal scaling via containerization (Docker).
*   **NFR-ARCH-03:** Python 3.10+ shall be used for the core engine, utilizing vectorized operations (Pandas/NumPy) for performance.
