# Sequence Diagrams — ClassSync AI

## Overview

This document presents Sequence Diagrams for **ClassSync AI**. These diagrams illustrate the step-by-step flow of messages between the user, the interface, and the system components to complete specific tasks.

---

## 1. Timetable Generation Workflow

This diagram shows the core process: how the system takes user input, runs the optimization engine, and saves the result.

```mermaid
sequenceDiagram
    autonumber
    actor User as University Admin
    participant UI as Web Interface
    participant API as Backend API
    participant DB as Database
    participant Engine as Optimization Engine

    %% Step 1: Initiation
    User->>UI: Click "Generate Timetable"
    UI->>API: POST /schedule/generate
    
    %% Step 2: Preparation
    activate API
    API->>DB: Fetch Courses, Teachers, Rooms
    activate DB
    DB-->>API: Return Dataset
    deactivate DB
    
    API->>DB: Fetch Constraints
    activate DB
    DB-->>API: Return Rules (Hard/Soft)
    deactivate DB

    %% Step 3: Execution
    API->>Engine: Start Optimization Job
    activate Engine
    
    Note right of Engine: Genetic Algorithm Running...<br/>(Selection, Crossover, Mutation)
    
    Engine->>Engine: Validate Hard Constraints
    Engine->>Engine: Score Soft Constraints
    
    %% Step 4: Completion
    Engine-->>API: Return Best Schedule
    deactivate Engine

    %% Step 5: Saving & Display
    API->>DB: Save Timetable Entries
    activate DB
    DB-->>API: Confirmation
    deactivate DB
    
    API-->>UI: Generation Complete (Success)
    deactivate API
    
    UI-->>User: Display Timetable View
```

### Explanation
1.  **Initiation**: The Admin starts the process from the dashboard.
2.  **Preparation**: The Backend gathers all necessary data (who is teaching what, which rooms are available) and the rules (constraints) from the database.
3.  **Execution**: The "Brain" (Optimization Engine) runs the Genetic Algorithm. It iteratively improves the schedule until it finds a conflict-free solution.
4.  **Completion**: The best schedule is sent back to the API.
5.  **Saving**: The result is permanently stored in the database, and the user sees the final timetable.

---

## 2. AI-Assisted Configuration Workflow

This diagram shows how the AI Agent helps the user modify rules using natural language.

```mermaid
sequenceDiagram
    autonumber
    actor User as University Admin
    participant Chat as AI Chat Panel
    participant LLM as AI Model (GPT/Gemini)
    participant API as Backend API

    %% Step 1: User Request
    User->>Chat: "Don't schedule labs on Fridays"
    Chat->>LLM: Send User Prompt + Tool Context
    
    %% Step 2: AI Reasoning
    activate LLM
    Note right of LLM: AI interprets intent:<br/>"Add Constraint: Block Friday Labs"
    
    LLM-->>Chat: Call Tool: update_constraint(Labs, Friday, Blocked)
    deactivate LLM

    %% Step 3: Confirmation
    Chat-->>User: "I will block all labs on Fridays. Confirm?"
    User->>Chat: "Yes, proceed."

    %% Step 4: Execution
    Chat->>API: POST /constraints/update
    activate API
    API-->>Chat: Success (Constraint Added)
    deactivate API

    %% Step 5: Feedback
    Chat-->>User: "Done! Labs are now blocked on Fridays."
```

### Explanation
1.  **User Request**: The user speaks naturally, asking for a change.
2.  **Interpretation**: The AI translates the English sentence into a specific system command.
3.  **Confirmation**: For safety, the system asks the user to confirm the change before applying it.
4.  **Execution**: The system updates the rules in the background.
5.  **Feedback**: The user is notified that the rule is now active.
