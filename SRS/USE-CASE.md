# Use Case Model — ClassSync AI

## Overview

This document defines the functional requirements of **ClassSync AI** through a Use Case Model. It captures the interaction between the primary actors (users) and the system to achieve specific goals, such as generating a conflict-free timetable.

## Use Case Diagram

```mermaid
usecaseDiagram
    actor "University Admin" as Admin
    actor "AI Assistant" as AI

    package "Authentication" {
        usecase "Login / Register" as UC1
    }

    package "Data Management" {
        usecase "Upload Datasets" as UC2
        usecase "Validate Data" as UC3
    }

    package "Configuration" {
        usecase "Configure Constraints" as UC4
        usecase "Set Preferences" as UC5
    }

    package "Scheduling" {
        usecase "Generate Timetable" as UC6
        usecase "View Timetable" as UC7
        usecase "Export Timetable" as UC8
    }

    package "AI Interaction" {
        usecase "Ask for Help" as UC9
        usecase "Run 'What-If' Scenarios" as UC10
        usecase "Explain Schedule" as UC11
    }

    %% Relationships
    Admin --> UC1
    Admin --> UC2
    Admin --> UC4
    Admin --> UC6
    Admin --> UC7
    Admin --> UC8
    Admin --> UC9

    %% System Dependencies
    UC2 ..> UC3 : <<include>>
    UC4 <.. UC5 : <<extend>>
    
    %% AI Interactions
    UC9 --> AI
    UC10 --> AI
    UC11 --> AI
    
    %% AI assisting in other areas
    UC3 <.. AI : <<assists>>
    UC4 <.. AI : <<assists>>
```

## 1. Actors

| Actor | Description |
| :--- | :--- |
| **University Admin** | The primary user responsible for setting up the semester, uploading data, and finalizing the schedule. |
| **AI Assistant** | An intelligent system component (Actor) that helps the user validate data, configure rules via chat, and understand the results. |

## 2. Use Case Descriptions

### UC1: Login / Register
*   **Goal**: Access the system securely.
*   **Description**: User enters credentials to access their institution's dashboard.

### UC2: Upload Datasets
*   **Goal**: Provide the necessary data for scheduling.
*   **Description**: The Admin uploads CSV/Excel files containing Courses, Teachers, Rooms, and Student Sections.
*   **Includes**: **Validate Data (UC3)** - The system automatically checks for errors (e.g., duplicate IDs, missing names) immediately after upload.

### UC4: Configure Constraints
*   **Goal**: Define the rules for the schedule.
*   **Description**: The Admin sets "Hard Constraints" (rules that cannot be broken, e.g., "No double booking") and "Soft Constraints" (preferences, e.g., "Minimize gaps").
*   **AI Assistance**: The Admin can ask the AI, *"Make sure no labs are on Friday,"* and the AI will update the configuration automatically.

### UC6: Generate Timetable
*   **Goal**: Create the actual schedule.
*   **Description**: The Admin clicks "Generate". The system runs its optimization algorithm to produce a conflict-free timetable within 60 seconds.

### UC8: Export Timetable
*   **Goal**: Share the results.
*   **Description**: The Admin downloads the final timetable in various formats (PDF, Excel, Image) to distribute to faculty and students.

### UC9: Ask for Help (AI Chat)
*   **Goal**: Get assistance using natural language.
*   **Description**: The Admin types questions into the chat panel, such as *"How do I upload data?"* or *"Why did the generation fail?"*.

### UC10: Run 'What-If' Scenarios
*   **Goal**: Test changes without breaking the current schedule.
*   **Description**: The Admin asks the AI, *"What happens if we close Building A?"*. The system runs a simulation and shows the impact on the schedule.
