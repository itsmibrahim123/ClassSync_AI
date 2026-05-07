# ClassSync AI — System Requirements Specification (Simplified & Detailed)

**Version:** 1.1  
**Type:** Generalized System Behavior & Architecture  
**Based On:** System Sequence Diagrams, Class Models, and Operational Use Cases.

---

## 1. System Overview

**ClassSync AI** is an intelligent scheduling platform for universities. It solves the complex problem of assigning courses to teachers and rooms without conflicts. It combines a powerful **Genetic Algorithm (Optimization Engine)** to doing the heavy calculation with an **AI Assistant (LLM)** that allows users to talk to the system in plain English.

The system is designed to be **Cloud-Native**, **Secure**, and **Fast**, generating complete schedules for medium-sized institutions in under 60 seconds.

---

## 2. Core Functional Behaviors
*Detailed breakdown of what the system does, organized by workflow.*

### 2.1 Managing Institutional Data (The Inputs)
Before scheduling can happen, the system must know the resources available.
*   **Universal Upload:** The system must accept data uploads in common standard formats (**CSV** and **Excel/XLSX**).
*   **Instant Validation:** As soon as a file is uploaded, the system must read it and check for logical errors.
    *   *Detail:* It must catch duplicates (e.g., two courses with the same code) and missing data (e.g., a room with no capacity).
*   **AI Diagnostics:** The AI Agent must be able to "read" these datasets to find subtle issues (e.g., "You have more students than total room capacity") and suggest fixes to the user.
*   **Secure Storage:** Validated files must be saved immediately to secure cloud storage (S3) so they are never lost.

### 2.2 Configuring Rules & Constraints (The Logic)
The schedule is built based on rules. The system allows these to be set manually or via conversation.
*   **Hard Constraints (The "Must-Haves"):** The system must strictly enforce these rules. If any are broken, the schedule is considered invalid.
    *   *Teacher Reality:* A teacher cannot be in two locations at the same time.
    *   *Room Reality:* A room cannot host two different classes at the same time.
    *   *Student Reality:* A specific group of students (Section) cannot attend two classes at once.
    *   *Time Reality:* Classes must fit strictly within defined slots (e.g., a 90-minute class cannot go into a 60-minute slot).
*   **Soft Constraints (The "Nice-to-Haves"):** The system must try to satisfy these but can compromise if necessary.
    *   *Detail:* Minimizing gaps in a teacher's day, avoiding late-night classes, or balancing room usage.
*   **Natural Language Configuration:** Users must be able to set rules by typing sentences like *"No classes on Friday afternoons."*
    *   *Behavior:* The AI interprets this, maps it to a specific system rule, and **must ask for confirmation** ("I will block all Friday PM slots. Confirm?") before applying it.

### 2.3 generating the Timetable (The Engine)
This is the core "brain" of the system, defined by the Genetic Algorithm.
*   **Process Initiation:** When the user clicks "Generate", the API retrieves all Courses, Teachers, Rooms, and Rules from the database.
*   **Evolutionary Optimization:** The engine must simulate natural selection:
    1.  Create random schedules.
    2.  "Punish" schedules with conflicts (bad fitness score).
    3.  "Reward" schedules that meet preferences (good fitness score).
    4.  Mix and match the best ones to create better schedules.
*   **Speed Guarantee:** The system must complete this complex process for a standard dataset (approx. 200 courses, 80 teachers) in **under 60 seconds**.
*   **Conflict Resolution:** If a perfect schedule is mathematically impossible, the system must return the "best possible" version and clearly highlight the remaining conflicts.

### 2.4 AI Assistant & "What-If" Analysis
The AI acts as a smart layer between the user and the complex code.
*   **Explanation Capability:** The user can ask *"Why is Mr. Smith teaching at 8 AM?"* and the AI must analyze the constraints (e.g., "Because his preferred slot at 10 AM was taken by a higher-priority lab") and explain it simply.
*   **Scenario Simulation:** The system must support safe experimentation.
    *   *Detail:* A user can say *"What if we close Building A?"*. The system runs a **Shadow Schedule** in the background, compares it to the real one, and reports the impact without messing up the actual data.

### 2.5 Outputs & Visualization
*   **Interactive Views:** Users must be able to view the final result as a grid, filtered by:
    *   **Teacher:** See one professor's week.
    *   **Room:** See when a specific lab is occupied.
    *   **Section:** See the agenda for a specific batch of students.
*   **Universal Export:** The system must generate files for external use: **PDF** (for printing), **Excel** (for admin editing), and **JSON** (for developers).

---

## 3. Data Blueprint (Entities)
*Simple definitions of the "Things" the system manages.*

| Entity | Description & Key Details |
| :--- | :--- |
| **Institution** | The university or college using the software. All data is strictly locked to one Institution (Multi-tenancy). |
| **User** | A person logging in. Must have a specific **Role** (Admin, Coordinator, Viewer) to determine what they can change. |
| **Course** | A subject to be taught. **Must have:** A unique code, a name, and a specific duration (how long one session lasts). |
| **Teacher** | An instructor. **Must have:** A name, email, and "Availability" (times they *cannot* work). |
| **Room** | A physical space. **Must have:** Capacity (how many seats), Type (Lecture Hall vs. Lab), and a Name. |
| **Student Section** | A group of students who take classes together. **Must have:** A size (count) to ensure they fit in the assigned rooms. |
| **Timetable Entry** | A single scheduled class. **Links together:** One Course + One Teacher + One Room + One Time Slot. |

---

## 4. Operational Standards (Non-Functional Requirements)
*The rules for how the system must perform.*

### 4.1 Speed & Responsiveness
*   **Generation Time:** The heavy lifting (scheduling) must happen in **≤ 60 seconds**.
*   **Interface Speed:** Clicking buttons or loading pages must take **≤ 2 seconds**.
*   **AI Latency:** When chatting with the AI, replies must appear within **2 to 5 seconds**.

### 4.2 Security & Safety
*   **Data Isolation:** Data from University A must **never** be visible to University B.
*   **Encryption:** All data traveling over the internet must be encrypted (HTTPS).
*   **Safe AI:** The AI is **never** allowed to change a rule or start a process without explicitly asking *"Do you want me to do this?"* first.

### 4.3 Reliability
*   **Uptime:** The system should be available 99.5% of the time.
*   **Auto-Save:** If a user is working on rules, the system must save their work automatically so nothing is lost if the internet disconnects.
*   **Graceful Failure:** If the scheduler fails (e.g., bad data), it must tell the user exactly what went wrong instead of just crashing.

---

## 5. Summary of System Logic (Sequence Flow)
*How the pieces talk to each other.*

1.  **User** uploads files to the **Web UI**.
2.  **Web UI** sends files to the **API**, which checks them and saves them to the **Database**.
3.  **User** tells the **AI**: *"No classes on Friday."*
4.  **AI** asks **User**: *"Confirm?"* -> **User** says *"Yes."* -> **AI** updates the **Database**.
5.  **User** clicks *"Generate"*.
6.  **API** wakes up the **Optimization Engine**.
7.  **Engine** pulls all data, runs the **Genetic Algorithm**, and finds the best fit.
8.  **Engine** saves the result to the **Database**.
9.  **Web UI** shows the new colorful Timetable to the **User**.
