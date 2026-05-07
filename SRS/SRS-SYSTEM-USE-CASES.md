# Software Requirements Specification (SRS) - System Use Cases
**Project:** ClassSync AI  
**Version:** 1.0  
**Date:** 2024  

---

## 1. Introduction
This document outlines the formal System Use Cases for **ClassSync AI**, derived from the system's architectural artifacts, sequence diagrams, and use case models. These use cases define the interactions between the primary actors (University Admin, AI Assistant) and the system.

---

## 2. System Use Cases

### UC1: Login / Register

**Use Case Number:** UC1  
**Use Case Name:** Login / Register  
**Summary:** The user authenticates with the system to access the dashboard and institution-specific data.  
**Priority:** High  
**Preconditions:**  
1. The user has a valid email and password (for Login) or a valid email (for Register).  
2. The system database is accessible.  
**Postconditions:**  
1. The user is authenticated.  
2. A secure session (JWT) is established.  
3. The user is redirected to the Dashboard.  
**Primary Actor(s):** University Admin  
**Secondary Actor(s):** System  
**Trigger:** User navigates to the landing page and selects "Login" or "Register".  

**Main Scenario:**  
1. **User** enters email and password on the login screen.  
2. **User** clicks the "Login" button.  
3. **System** validates the format of the input credentials.  
4. **System** verifies credentials against the database.  
5. **System** generates a JWT token for the session.  
6. **System** redirects the **User** to the main Dashboard.  

**Extensions / Alternate Flows:**  
*3a. Invalid Email/Password Format:*  
    1. **System** displays a validation error message.  
    2. **User** re-enters credentials.  
*4a. Authentication Failed:*  
    1. **System** displays an "Invalid credentials" error.  
    2. **User** retries or selects "Forgot Password".  

**Open Issues or Constraints:**  
*   Passwords must be stored using bcrypt/Argon2 hashing (NFR-SEC-02).

---

### UC2: Upload Datasets

**Use Case Number:** UC2  
**Use Case Name:** Upload Datasets  
**Summary:** The Admin uploads academic data files (CSV/XLSX) required for scheduling.  
**Priority:** High  
**Preconditions:**  
1. **User** is logged in (UC1).  
**Postconditions:**  
1. Files are stored in S3-compatible storage.  
2. Dataset metadata is recorded in the database.  
3. **Validate Data (UC3)** is triggered.  
**Primary Actor(s):** University Admin  
**Secondary Actor(s):** System, AI Assistant  
**Trigger:** User selects "Upload Data" from the Dashboard.  

**Main Scenario:**  
1. **User** selects the file type to upload (Courses, Teachers, Rooms, or Sections).  
2. **User** drags and drops the file or selects it via the file browser.  
3. **System** receives the file and initiates the upload process.  
4. **System** includes **Validate Data (UC3)** to check file integrity and schema.  
5. **System** saves the valid file to cloud storage.  
6. **System** updates the dataset status indicator on the Dashboard.  

**Extensions / Alternate Flows:**  
*4a. Validation Fails:*  
    1. **System** rejects the upload.  
    2. **System** (via AI Assistant) displays specific error details (e.g., "Missing column 'Teacher ID'").  
    3. **User** corrects the file and re-uploads.  

**Open Issues or Constraints:**  
*   Must support CSV and XLSX formats (FR-DATA-01).

---

### UC3: Validate Data

**Use Case Number:** UC3  
**Use Case Name:** Validate Data  
**Summary:** The system checks uploaded datasets for schema compliance, duplicates, and logical errors.  
**Priority:** High  
**Preconditions:**  
1. A file upload process (UC2) has been initiated.  
**Postconditions:**  
1. Dataset is marked as "Valid" or "Invalid".  
2. Error report is generated if invalid.  
**Primary Actor(s):** System  
**Secondary Actor(s):** AI Assistant  
**Trigger:** Automatically triggered by **Upload Datasets (UC2)**.  

**Main Scenario:**  
1. **System** parses the uploaded file.  
2. **System** checks for mandatory columns and correct data types.  
3. **System** checks for duplicate entries (e.g., duplicate Course Codes).  
4. **AI Assistant** analyzes data for logical inconsistencies (e.g., "Room capacity < Course enrollment").  
5. **System** returns the validation status to the User.  

**Extensions / Alternate Flows:**  
*N/A - Internal System Process*  

**Open Issues or Constraints:**  
*   Validation must complete in ≤3 seconds for standard files (NFR-PERF-02).

---

### UC4: Configure Constraints

**Use Case Number:** UC4  
**Use Case Name:** Configure Constraints  
**Summary:** The Admin defines Hard Constraints (mandatory rules) and Soft Constraints (preferences) for the schedule.  
**Priority:** High  
**Preconditions:**  
1. **User** is logged in.  
**Postconditions:**  
1. Constraint profile is updated in the database.  
**Primary Actor(s):** University Admin  
**Secondary Actor(s):** AI Assistant, System  
**Trigger:** User navigates to the "Constraints" panel or issues a natural language command.  

**Main Scenario (UI Flow):**  
1. **User** navigates to the Constraints Configuration screen.  
2. **System** fetches and displays current Hard and Soft constraints.  
3. **User** modifies constraint parameters (e.g., toggles "Block Friday Labs", adjusts "Teacher Gap" weights).  
4. **User** clicks "Save".  
5. **System** persists the new configuration to the database.  

**Extensions / Alternate Flows:**  
*Alternate Flow: AI-Assisted Configuration (Sequence Diagram 2)*  
1. **User** types a command in the AI Chat (e.g., "Don't schedule labs on Fridays").  
2. **AI Assistant** interprets the intent and maps it to a tool call (`update_constraint`).  
3. **AI Assistant** asks for confirmation: "I will block all labs on Fridays. Confirm?"  
4. **User** confirms ("Yes").  
5. **System** executes the update and confirms success.  

**Open Issues or Constraints:**  
*   All constraint modifications via AI require explicit user confirmation (FR-AI-02).

---

### UC5: Set Preferences

**Use Case Number:** UC5  
**Use Case Name:** Set Preferences  
**Summary:** The Admin fine-tunes Soft Constraints and global scheduling preferences (e.g., time slot duration).  
**Priority:** Medium  
**Preconditions:**  
1. **User** is accessing the Constraints panel.  
**Postconditions:**  
1. Preference weights and settings are updated.  
**Primary Actor(s):** University Admin  
**Secondary Actor(s):** System  
**Trigger:** User interacts with specific "Preferences" or "Soft Constraints" controls.  

**Main Scenario:**  
1. **User** extends the configuration process (**Extends UC4**).  
2. **User** adjusts sliders for Soft Constraint weights (e.g., High priority for "Minimize Building Changes").  
3. **User** selects global settings (e.g., "Timeslot Duration: 90 minutes").  
4. **User** saves changes.  
5. **System** applies these preferences to the scoring algorithm.  

**Extensions / Alternate Flows:**  
*N/A*  

**Open Issues or Constraints:**  
*   Treated as a distinct logical extension of general constraint configuration in the Use Case Model.

---

### UC6: Generate Timetable

**Use Case Number:** UC6  
**Use Case Name:** Generate Timetable  
**Summary:** The system runs the Genetic Algorithm optimization engine to produce a conflict-free timetable.  
**Priority:** Critical  
**Preconditions:**  
1. Datasets (Courses, Teachers, Rooms) are uploaded and valid.  
2. Subscription status is active.  
**Postconditions:**  
1. A new Timetable is generated and saved to the database.  
2. User is presented with the results.  
**Primary Actor(s):** University Admin  
**Secondary Actor(s):** System, Optimization Engine  
**Trigger:** User clicks the "Generate Timetable" button.  

**Main Scenario (Matches Sequence Diagram 1):**  
1. **User** clicks "Generate Timetable".  
2. **System** (API) fetches active datasets and constraints from the database.  
3. **System** validates Hard Constraints against the data.  
4. **Optimization Engine** initiates the Genetic Algorithm (Selection, Crossover, Mutation).  
5. **Optimization Engine** iteratively improves the schedule to satisfy Hard Constraints and maximize Soft Constraint scores.  
6. **System** provides real-time progress feedback to the User.  
7. **Optimization Engine** returns the best schedule found.  
8. **System** saves the timetable entries to the database.  
9. **System** displays the "Generation Complete" message and renders the Timetable View.  

**Extensions / Alternate Flows:**  
*7a. Generation Timeout / Failure:*  
    1. **System** detects timeout (> 60 seconds) or failure to converge.  
    2. **System** saves the best partial solution (if available) or logs the error.  
    3. **System** notifies **User** of the failure and suggests relaxing constraints.  

**Open Issues or Constraints:**  
*   Must complete within 60 seconds for standard datasets (NFR-PERF-01).

---

### UC7: View Timetable

**Use Case Number:** UC7  
**Use Case Name:** View Timetable  
**Summary:** The Admin views the generated schedule in various formats (Grid, List) filtered by resource.  
**Priority:** High  
**Preconditions:**  
1. A timetable has been successfully generated (UC6).  
**Postconditions:**  
1. Schedule data is visualized.  
**Primary Actor(s):** University Admin  
**Secondary Actor(s):** System  
**Trigger:** User navigates to the "Timetable" page.  

**Main Scenario:**  
1. **User** selects a view mode (By Teacher, By Room, or By Section).  
2. **System** fetches the relevant schedule entries from the database.  
3. **System** renders the interactive color-coded grid.  
4. **User** clicks on a specific session to view details (Course Name, Time, Room).  

**Extensions / Alternate Flows:**  
*4a. Filter Data:*  
    1. **User** applies a filter (e.g., "Show only Computer Science Labs").  
    2. **System** updates the view to match the filter.  

**Open Issues or Constraints:**  
*   UI must remain responsive (<2s load time).

---

### UC8: Export Timetable

**Use Case Number:** UC8  
**Use Case Name:** Export Timetable  
**Summary:** The Admin downloads the timetable in a portable format for distribution.  
**Priority:** Medium  
**Preconditions:**  
1. A timetable exists.  
**Postconditions:**  
1. A file (XLSX, CSV, PDF, PNG, or ZIP) is downloaded to the User's device.  
**Primary Actor(s):** University Admin  
**Secondary Actor(s):** System  
**Trigger:** User clicks "Export" on the Timetable View.  

**Main Scenario:**  
1. **User** clicks the "Export" button.  
2. **User** selects the desired format (e.g., PDF).  
3. **System** generates the file based on the current schedule data.  
4. **System** provides a download link.  
5. **User** downloads the file.  

**Extensions / Alternate Flows:**  
*N/A*  

**Open Issues or Constraints:**  
*   Supported formats: XLSX, CSV, PNG, PDF, JSON, ZIP.

---

### UC9: Ask for Help (AI Chat)

**Use Case Number:** UC9  
**Use Case Name:** Ask for Help  
**Summary:** The user interacts with the AI Assistant using natural language to get help, explanations, or navigation assistance.  
**Priority:** Medium  
**Preconditions:**  
1. **User** is logged in.  
**Postconditions:**  
1. AI provides a text response or performs an action.  
**Primary Actor(s):** University Admin  
**Secondary Actor(s):** AI Assistant  
**Trigger:** User types into the AI Chat Panel.  

**Main Scenario:**  
1. **User** types a query (e.g., "How do I upload data?").  
2. **AI Assistant** analyzes the text to determine intent.  
3. **AI Assistant** retrieves relevant documentation or context.  
4. **AI Assistant** responds with step-by-step instructions or an answer.  

**Extensions / Alternate Flows:**  
*2a. Tool Invocation:*  
    1. If the query implies an action (e.g., "Run the scheduler"), **AI Assistant** triggers the relevant Use Case (e.g., UC6).  

**Open Issues or Constraints:**  
*   AI must use GPT-4.1 or Gemini 2.0 (FR-AI-21).

---

### UC10: Run 'What-If' Scenarios

**Use Case Number:** UC10  
**Use Case Name:** Run 'What-If' Scenarios  
**Summary:** The Admin simulates changes to constraints to see the potential impact on the schedule without overwriting the master timetable.  
**Priority:** Medium  
**Preconditions:**  
1. A baseline schedule exists.  
**Postconditions:**  
1. A simulation report is displayed comparing the baseline vs. the new scenario.  
**Primary Actor(s):** University Admin  
**Secondary Actor(s):** AI Assistant, System  
**Trigger:** User asks AI "What happens if..." or selects "Simulate Scenario" in UI.  

**Main Scenario:**  
1. **User** proposes a change (e.g., "What if we close Building A?").  
2. **AI Assistant** interprets this as a temporary constraint set.  
3. **System** runs a shadow instance of **Generate Timetable (UC6)** using the temporary constraints.  
4. **System** compares the shadow schedule with the current master schedule.  
5. **AI Assistant** summarizes the impact (e.g., "Closing Building A causes 5 unresolvable conflicts").  

**Extensions / Alternate Flows:**  
*N/A*  

**Open Issues or Constraints:**  
*   Simulation results must not overwrite the production timetable unless explicitly applied.

---

### UC11: Explain Schedule

**Use Case Number:** UC11  
**Use Case Name:** Explain Schedule  
**Summary:** The AI Assistant explains why a specific class was scheduled at a specific time/room.  
**Priority:** Medium  
**Preconditions:**  
1. A timetable is visible (UC7).  
**Postconditions:**  
1. Explanation is displayed to the user.  
**Primary Actor(s):** University Admin  
**Secondary Actor(s):** AI Assistant  
**Trigger:** User clicks "Explain this Slot" or asks "Why is [Course] here?".  

**Main Scenario:**  
1. **User** selects a scheduled session and requests an explanation.  
2. **AI Assistant** retrieves the constraints and resource availability for that session.  
3. **AI Assistant** analyzes why alternative slots were rejected (e.g., "Teacher was unavailable", "Room overlap").  
4. **AI Assistant** provides a natural language explanation (e.g., "This was the only slot where Teacher X and Room Y were both free").  

**Extensions / Alternate Flows:**  
*N/A*  

**Open Issues or Constraints:**  
*   Requires traceability of GA decision-making or post-hoc analysis.
