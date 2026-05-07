# SRS - ClassSync AI

## Part 2: System Features & Functional Requirements

Version: 1.0

---

# 3. System Features

This section provides a structured overview of ClassSync AI’s features.

---

## 3.1 Dataset Upload & Management

### **Description**

Allows institutions to upload, validate, and manage academic datasets required for timetable generation.

### **Features**

- Upload CSV/XLSX files for:
  - Courses
  - Teachers
  - Rooms
  - Sections
  - Timeslot templates
- Automatic schema validation
- Duplicate detection
- AI-assisted data cleaning
- File versioning and reupload support
- Dataset completeness indicator

---

## 3.2 Constraint Configuration Module

### **Description**

Provides full configuration of scheduling constraints, including defaults, optional rules, and AI-assisted adjustments.

### **Features**

- Configure hard constraints
- Configure soft constraints
- Toggle optional constraints
- Modify timeslot duration (60/90/120 min)
- Apply AI-generated recommendations
- Reset all constraints to system defaults
- Save/load constraint presets

---

## 3.3 Optimization Engine (Scheduler)

### **Description**

The core engine generating optimized, clash-free timetables.

### **Features**

- Multi-pass optimization
- Hard constraint enforcement
- Soft constraint scoring
- Optional constraint integration
- Conflict detection & auto-resolution
- Execution time target: ≤ 60 seconds
- Scales to:
  - 200+ courses
  - 80+ teachers
  - 60+ rooms

---

## 3.4 Export & Visualization Module

### **Description**

Generates timetable files and visual outputs.

### **Supported Formats**

- XLSX
- CSV
- PNG image
- PDF
- JSON
- ZIP bundle

### **Features**

- Per-section, per-teacher, per-room views
- Interactive timetable viewer
- Color-coded visualization
- AI-generated summary of schedule

---

## 3.5 AI Agent Module

### **Description**

Provides conversational interface powered by GPT-4.1 (primary) and Gemini 2.0 (secondary).

### **Features**

- Natural-language constraint configuration
- Dataset diagnosis & correction
- Timetable explanation (why-choices)
- Run what-if scenarios
- Suggest improvements
- Assist onboarding
- Modify constraints (requires confirmation)
- Reset constraints to default
- Structured tool-calling interface

---

## 3.6 Authentication & User Management

### **Description**

Handles secure cloud login and user roles.

### **Features**

- Email + password authentication
- JWT-based session management
- Roles:
  - Admin
  - Coordinator
  - Viewer
- Password reset
- Institution-level data isolation

---

## 3.7 Subscription & Free Trial Module

### **Description**

Implements SaaS billing prerequisites.

### **Features**

- Free trial activation
- Subscription validation
- Institution billing metadata
- Restrict timetable generation if subscription expires

---

# 4. Functional Requirements (FRs)

This section defines detailed, testable system behaviors.

---

## 4.1 Dataset Upload Requirements

### **FR-1**

System shall allow uploading CSV/XLSX datasets for courses, teachers, rooms, and sections.

### **FR-2**

System shall validate uploaded files and detect missing or malformed fields.

### **FR-3**

AI Agent shall highlight issues and suggest corrections.

### **FR-4**

System shall securely store validated files in cloud storage.

### **FR-5**

System shall maintain dataset version history.

---

## 4.2 Constraint Configuration Requirements

### **FR-6**

System shall allow users to modify all hard and soft constraints.

### **FR-7**

System shall allow toggling optional constraints (including room capacity).

### **FR-8**

System shall support subdividable timeslots (60/90/120 minutes).

### **FR-9**

System shall allow resetting constraints to defaults.

### **FR-10**

AI Agent shall modify constraints only after user confirmation.

---

## 4.3 Optimization Engine Requirements

### **FR-11**

System shall generate a clash-free timetable respecting all hard constraints.

### **FR-12**

System shall optimize soft constraints using a scoring algorithm.

### **FR-13**

System shall complete generation **within 60 seconds** for standard dataset size:

- 200 courses
- 80 teachers
- 60 rooms

### **FR-14**

System shall detect and report remaining conflicts if present.

### **FR-15**

System shall support re-running generation with updated constraints.

---

## 4.4 AI Agent Requirements

### **FR-16**

AI Agent shall interpret natural-language instructions and convert them into operations.

### **FR-17**

AI Agent may modify both hard and soft constraints but must always prompt before applying changes.

### **FR-18**

AI Agent shall detect and explain dataset inconsistencies.

### **FR-19**

AI Agent shall explain placement of any scheduled class upon request.

### **FR-20**

AI Agent shall run “what-if” simulations and compare outputs.

### **FR-21**

AI Agent shall use GPT-4.1 as primary LLM and Gemini 2.0 as secondary.

---

## 4.5 Export Requirements

### **FR-23**

System shall export timetables in XLSX, CSV, PNG, PDF, JSON, and ZIP formats.

### **FR-24**

System shall allow exporting per-section, per-room, and per-teacher timetables.

---

## 4.6 Authentication Requirements

### **FR-25**

System shall authenticate users via email/password.

### **FR-26**

System shall enforce role-based access.

---

## 4.7 Subscription Requirements

### **FR-27**

System shall provide a free trial for new institutions.

### **FR-28**

System shall validate subscription status before generating a timetable.

---
