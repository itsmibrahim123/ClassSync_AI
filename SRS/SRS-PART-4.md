# SRS - ClassSync AI

## Part 4: Non-Functional Requirements

Version: 1.0

---

# 8. Non-Functional Requirements (NFRs)

This section defines the quality attributes that ClassSync AI must satisfy for production deployment.

---

# 8.1 Performance Requirements

### **NFR-1: Timetable Generation Speed**

- The system shall generate a timetable for up to **200 courses, 80 teachers, and 60 rooms** in **≤60 seconds**.
- Optimization algorithms shall be time-efficient and scale gracefully for larger datasets.

### **NFR-2: UI Responsiveness**

- All screens shall load in **≤2 seconds** on a standard network connection.
- File upload validation shall complete in **≤3 seconds** for files under 5MB.

### **NFR-3: AI Agent Response Time**

- AI-generated responses to user queries shall be returned in **2–5 seconds** under normal load.
- Tool-calling operations shall complete within **≤10 seconds**, excluding timetable generation.

### **NFR-4: Availability**

- The SaaS platform shall target **99.5% uptime** monthly.

---

# 8.2 Security Requirements

### **NFR-5: Secure Authentication**

- Passwords shall be stored using **bcrypt** or **Argon2** hashing.
- JWT tokens shall be used for session authorization with regular rotation.

### **NFR-6: Data Isolation & Access Control**

- Institutions’ data must be **strictly isolated**.
- Users shall only access data associated with their institution.

### **NFR-7: HTTPS Enforcement**

- All external communication must occur over **HTTPS/TLS 1.2+**.

### **NFR-8: Algorithm Protection**

- Core optimization logic (Python files) shall be obfuscated to prevent reverse engineering.

---

# 8.3 Reliability Requirements

### **NFR-9: Error Recovery**

- System shall handle failures gracefully and generate meaningful AI-assisted error messages.
- Failed optimization attempts shall not corrupt stored data.

### **NFR-10: Auto-Save**

- User configuration (constraints) shall auto-save every **30 seconds**.

### **NFR-11: Retry Mechanism**

- API calls to external services (AI provider, storage) shall retry **3 times** with exponential backoff.

---

# 8.4 Scalability Requirements

### **NFR-12: Horizontal Scalability**

- Backend services shall support container-based scaling (Docker or equivalent).

### **NFR-13: Database Scalability**

- PostgreSQL database shall be optimized for:
  - Read-heavy operations
  - High concurrency
  - Indexing of frequently accessed fields

### **NFR-14: Multi-Tenant Support**

- All institutions’ data must be isolated via tenant-aware database schemas or keys.

---

# 8.5 Maintainability Requirements

### **NFR-15: Modular Architecture**

- Codebase shall be split into:
  - `classsync_api`
  - `classsync_core`
  - `classsync_agent`
  - `classsync_ui`

### **NFR-16: Documentation**

- All modules must include:
  - Inline comments
  - Docstrings
  - Updated README documentation

### **NFR-17: Configurability**

- Scheduling rules and constraints shall be stored externally in JSON/YAML files.

---

# 8.6 Usability Requirements

### **NFR-18: Ease of Use**

- The UI must be usable by non-technical academic staff.

### **NFR-19: Accessibility**

- High contrast colors and clear labels must be used.
- No color-only communication for critical elements.

### **NFR-20: Error Feedback**

- Errors must be displayed in plain English.
- AI Agent must provide suggestions for fixing issues.

---

# 8.7 Portability Requirements

### **NFR-21: Browser Support**

- Latest versions of:
  - Chrome
  - Firefox
  - Edge

### **NFR-22: Cloud Deployment**

- System shall be deployable on any modern cloud provider (AWS, GCP, Azure, Render, Fly.io).

---

# 8.8 Business Requirements

### **NFR-23: Subscription Model**

- SaaS system shall include:
  - Free Trial
  - Monthly Subscription
  - Annual Subscription

### **NFR-24: Institution Licensing**

- Each institution shall have its own subscription metadata.

---

# 8.9 Quality Attributes

| Attribute            | Requirement                                                              |
| -------------------- | ------------------------------------------------------------------------ |
| **Accuracy**         | No hard constraint violations unless user-approved.                      |
| **Reliability**      | Consistent results with validated data.                                  |
| **Robustness**       | AI handles ambiguous queries without system failure.                     |
| **Extensibility**    | New constraints or modules must be easily added.                         |
| **Interoperability** | Multiple export formats shall allow integration with LMS/export systems. |

---

# 8.10 Legal & Compliance Requirements

### **NFR-25: Data Privacy**

- User/Institution data shall not be used for LLM training.

### **NFR-26: Logging Compliance**

- All AI tool calls, constraint modifications, and scheduling operations shall be logged for audit.

---
