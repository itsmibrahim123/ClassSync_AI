# SRS — ClassSync AI

## Part 1: Introduction & Overall Description

Version: 1.0
Prepared By: Khadijah (Project Owner)

---

# 1. Introduction

## 1.1 Purpose

This Software Requirements Specification (SRS) defines the functional, non-functional, architectural, and operational requirements for **ClassSync AI**, a cloud-based, AI-powered university timetabling system.

The purpose of this SRS is to:

- Formalize the system behavior and capabilities
- Guide backend, frontend, and AI-agent development
- Provide documentation for stakeholders and institutions
- Serve as a baseline for testing, deployment, and scaling

---

## 1.2 Scope

ClassSync AI is a **SaaS scheduling platform** that generates optimized, clash-free university timetables using:

- A high-performance **Python optimization engine**
- A **web interface** for dataset upload, configuration, and visualization
- A **cloud-based AI Agent (GPT-4.1 / Gemini)** for natural-language interaction, constraint adjustments, explanations, and refinements

### System Includes:

1. **ClassSync Core Engine**
2. **Web UI (SaaS)**
3. **AI Agent Layer**
4. **Export & Visualization Module**
5. **Authentication & Multi-Tenancy**
6. **Subscription + Free Trial support**

---

## 1.3 Definitions & Acronyms

| Term                | Definition                                                             |
| ------------------- | ---------------------------------------------------------------------- |
| Hard Constraint     | A rule that must not be violated (e.g., teacher overlap)               |
| Soft Constraint     | A rule that may be violated with penalty (e.g., teacher gaps)          |
| Optional Constraint | User-toggleable rules (e.g., room capacity)                            |
| AI Agent            | Cloud LLM system that interprets user commands and calls backend tools |
| Section             | Student batch taking the same set of classes                           |
| Timeslot            | A defined scheduling period; may be subdivided (60/90/120 min)         |
| SaaS                | Software as a Service                                                  |
| LMS                 | Learning Management System (future)                                    |

---

## 1.4 References

- IEEE 830 SRS Standard
- ClassSync Core Python modules
- FastAPI backend endpoints
- Constraint configuration templates
- GPT-4.1 / Gemini tool-calling documentation

---

## 1.5 Overview of SRS Document

This SRS includes:

- Part 1 — Introduction & Overall Description
- Part 2 — System Features & Functional Requirements
- Part 3 — External Interface Requirements
- Part 4 — Non-Functional Requirements
- Part 5 — Architecture, Workflows, Data Models
- Part 6 — Traceability Matrix, Risks, Acceptance Criteria, Summary

---

# 2. Overall Description

## 2.1 Product Perspective

ClassSync AI is a **new SaaS product** with the following architectural layers:

Web UI → Backend API → Core Engine → DB/Storage

↘ AI Agent ↙

The system is modular and cloud-hosted, with an AI layer providing natural-language scheduling assistance.

---

## 2.2 Product Functions (Summary)

- Upload & validate datasets (teachers, courses, rooms, sections)
- Configure constraints (hard, soft, optional)
- Automatically subdivide timeslots
- Generate clash-free timetables in ≤60s
- Run AI-assisted scenario simulations
- Explain scheduling decisions
- Export timetables (XLSX, CSV, PDF, PNG, ZIP)
- User authentication & subscription system

---

## 2.3 User Classes

| User Type   | Description                                                  |
| ----------- | ------------------------------------------------------------ |
| Admin       | Full control, dataset upload, constraint editing, generation |
| Coordinator | Adjust scheduling preferences, validate timetable            |
| Viewer      | Read-only timetable access                                   |
| Super Admin | SaaS system admin (manage institutions)                      |

---

## 2.4 Operating Environment

- **Backend:** Python 3.10+, FastAPI
- **AI:** OpenAI GPT-4.1 (primary), Gemini 2.0 (secondary)
- **Frontend:** Modern browser (Chrome/Edge/Firefox)
- **Database:** PostgreSQL
- **Storage:** S3-compatible cloud bucket

---

## 2.5 Constraints

- Cloud-only LLM access
- Performance requirement: generate timetable ≤ 60s
- Room capacity treated as optional constraint
- Scaling must support 200+ courses
- All constraint modifications require confirmation
- Ability to reset all constraints to default

---

## 2.6 User Documentation

- Online documentation page
- AI-powered contextual help
- Swagger/OpenAPI API documentation

---

## 2.7 Assumptions & Dependencies

### Assumptions:

- Institution provides structured datasets
- Required cloud infrastructure is available
- Users have internet connectivity

### Dependencies:

- FastAPI
- PostgreSQL
- S3 Storage
- OpenAI & Gemini APIs
- Pandas, NumPy, OpenPyXL

---
