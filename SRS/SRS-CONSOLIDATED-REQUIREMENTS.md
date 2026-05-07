# Software Requirements Specification (SRS) - Consolidated Requirements
**Project:** ClassSync AI  
**Version:** 1.0  
**Date:** 2024  

---

## 1. Introduction

This document formally defines the Functional and Non-Functional Requirements for **ClassSync AI**, a cloud-based University Timetabling System. These requirements are derived from the system's architectural diagrams, use case models, and sequence workflows. They serve as the primary source of truth for development, testing, and validation.

### 1.1 Scope
ClassSync AI automates the scheduling of university courses using a Genetic Algorithm (GA) optimization engine, accessible via a SaaS web interface and an AI Agent. The system allows administrators to upload academic datasets, configure constraints via natural language or UI controls, generate conflict-free timetables, and export results in multiple formats.

---

## 2. Functional Requirements (FR)

Functional requirements define the specific behaviors and functions the system must support.

### 2.1 Authentication & User Management
*   **FR-AUTH-01 (Login):** The system shall allow users to authenticate using an email address and password.
*   **FR-AUTH-02 (RBAC):** The system shall enforce Role-Based Access Control (RBAC) with at least the following roles: Admin (full access), Coordinator (limited editing), and Viewer (read-only).
*   **FR-AUTH-03 (Session Management):** The system shall manage user sessions securely using JWT (JSON Web Tokens).
*   **FR-AUTH-04 (Multi-Tenancy):** The system shall ensure data isolation between different institutions; a user from one institution must not access data from another.
*   **FR-AUTH-05 (Subscription Check):** The system shall validate the institution's subscription status or free-trial eligibility before allowing timetable generation.

### 2.2 Data Management (Inputs)
*   **FR-DATA-01 (Dataset Upload):** The system shall accept dataset uploads in CSV and XLSX formats for the following entities:
    *   Courses (Code, Name, Duration, Section)
    *   Teachers (Name, Availability, Load)
    *   Rooms (Capacity, Type, Name)
    *   Student Sections (Size, Name)
*   **FR-DATA-02 (Validation):** The system shall automatically validate uploaded files for schema compliance, missing fields, and duplicate entries immediately upon upload.
*   **FR-DATA-03 (Storage):** The system shall securely store validated raw dataset files in S3-compatible cloud storage.
*   **FR-DATA-04 (Versioning):** The system shall maintain version history for uploaded datasets to allow rollback or comparison.

### 2.3 Constraint Configuration
*   **FR-CONF-01 (Constraint Management):** The system shall allow users to view, enable, disable, and modify parameters for:
    *   **Hard Constraints:** (Mandatory) e.g., No teacher overlap, No room overlap.
    *   **Soft Constraints:** (Preferences) e.g., Minimize gaps, Reduce morning classes.
    *   **Optional Constraints:** (Toggleable) e.g., Enforce room capacity, Block Friday labs.
*   **FR-CONF-02 (Timeslot Definition):** The system shall support configurable timeslot durations (60, 90, or 120 minutes).
*   **FR-CONF-03 (Reset Defaults):** The system shall provide a function to reset all constraints to their system-default values.
*   **FR-CONF-04 (Natural Language Config):** The system shall accept natural language commands via the AI Agent to modify constraints (e.g., "Block all labs on Fridays") and convert them into structured system rules.

### 2.4 Optimization Engine (Scheduling)
*   **FR-SCHED-01 (Generation):** The system shall generate a valid, clash-free timetable by executing a Genetic Algorithm that evolves a population of schedules.
*   **FR-SCHED-02 (Conflict Resolution):** The system shall prioritize Hard Constraints; a schedule with Hard Constraint violations shall be considered invalid (Fitness = 0) unless explicitly overridden by the user.
*   **FR-SCHED-03 (Soft Optimization):** The system shall optimize the schedule based on a weighted sum of Soft Constraint satisfaction.
*   **FR-SCHED-04 (Performance Target):** The system shall complete the generation process for a standard dataset (200 courses, 80 teachers, 60 rooms) in 60 seconds or less.
*   **FR-SCHED-05 (Progress Feedback):** The system shall provide real-time feedback during generation (e.g., current generation number, best fitness score).

### 2.5 AI Agent & Assistant
*   **FR-AI-01 (Interpretation):** The AI Agent shall interpret user queries and map them to specific backend tools (`validate_data`, `update_constraint`, `run_scheduler`, etc.).
*   **FR-AI-02 (Confirmation Loop):** The AI Agent must request user confirmation before applying changes to constraints or triggering a new schedule generation.
*   **FR-AI-03 (Explanation):** The AI Agent shall provide explanations for specific scheduling decisions (e.g., "Why is Course A at 9 AM?") by analyzing the constraints and resource availability.
*   **FR-AI-04 (What-If Scenarios):** The system shall allow "What-If" simulations where the AI creates a temporary constraint set, generates a shadow schedule, and compares it to the current master schedule.
*   **FR-AI-05 (Dataset Diagnosis):** The AI Agent shall analyze uploaded datasets for logical inconsistencies (e.g., "Total course hours exceed room capacity") and suggest fixes.

### 2.6 Export & Visualization (Outputs)
*   **FR-EXP-01 (Timetable Views):** The system shall display the generated timetable in interactive grids filtered by:
    *   Student Section
    *   Teacher
    *   Physical Room
*   **FR-EXP-02 (File Export):** The system shall export the finalized timetable in the following formats:
    *   **XLSX:** Detailed spreadsheets with multiple tabs.
    *   **CSV:** Raw data for external processing.
    *   **PDF:** Formatted reports for printing.
    *   **PNG:** Visual images of the schedule grid.
    *   **JSON:** Structured data for API consumption.
    *   **ZIP:** A bundle containing all the above.

---

## 3. Non-Functional Requirements (NFR)

Non-functional requirements define the quality attributes of the system, such as performance, security, and reliability.

### 3.1 Performance & Scalability
*   **NFR-PERF-01 (Generation Speed):** The optimization engine must produce a feasible schedule for the target dataset size (approx. 1000 sessions) within **60 seconds**.
*   **NFR-PERF-02 (UI Latency):** Dashboard screens and standard interactions must load in **≤ 2 seconds** under normal network conditions.
*   **NFR-PERF-03 (AI Latency):** The AI Agent must return a response to standard queries within **2 to 5 seconds**.
*   **NFR-SCAL-01 (Concurrency):** The backend architecture shall support horizontal scaling via containerization (Docker) to handle multiple simultaneous institution generations.

### 3.2 Security & Compliance
*   **NFR-SEC-01 (Encryption):** All data in transit must be encrypted via **HTTPS/TLS 1.2+**.
*   **NFR-SEC-02 (Password Storage):** User passwords must be salted and hashed using strong algorithms (e.g., **bcrypt** or **Argon2**).
*   **NFR-SEC-03 (Data Privacy):** Institution data must be logically isolated in the database and must **not** be used to train the public LLM models.
*   **NFR-SEC-04 (Audit Logging):** All critical actions, specifically constraint modifications and AI tool invocations, must be logged for audit purposes.

### 3.3 Reliability & Availability
*   **NFR-REL-01 (Uptime):** The SaaS platform shall target a monthly availability of **99.5%**.
*   **NFR-REL-02 (Error Handling):** The system shall degrade gracefully; failed optimization runs must not corrupt existing data and should provide actionable error messages.
*   **NFR-REL-03 (Auto-Save):** User configurations and constraints shall be auto-saved to prevent data loss during session timeouts.

### 3.4 Maintainability & Architecture
*   **NFR-ARCH-01 (Modularity):** The system shall maintain a strict separation of concerns between the Frontend (React), Backend API (FastAPI), Core Engine (Python), and AI Service.
*   **NFR-ARCH-02 (Code Quality):** The optimization core shall use vectorized operations (Pandas/NumPy) where possible to ensure maintainability and performance.
*   **NFR-ARCH-03 (Obfuscation):** Proprietary algorithmic modules shall be obfuscated to protect intellectual property in deployed environments.

### 3.5 Usability
*   **NFR-USE-01 (Accessibility):** The web interface shall adhere to basic accessibility standards (high contrast, clear labeling) to support diverse user needs.
*   **NFR-USE-02 (Clarity):** Error messages and AI explanations must be presented in plain, non-technical language suitable for academic administrators.
