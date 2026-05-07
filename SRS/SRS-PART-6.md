# SRS — ClassSync AI

## Part 6: Traceability, Acceptance, Risks, and Final Summary

Version: 1.0

---

# 17. Requirement Traceability Matrix (RTM)

This matrix ensures each Functional Requirement (FR) is tied to system features, test cases, and acceptance criteria.

| Req ID | Requirement Summary                       | System Module       | Verification Method |
| ------ | ----------------------------------------- | ------------------- | ------------------- |
| FR-1   | Upload datasets                           | Dataset Module      | UI Test / API Test  |
| FR-2   | Validate datasets                         | Dataset Module      | Validation Test     |
| FR-3   | AI-assisted validation                    | AI Agent            | Agent Test          |
| FR-4   | Store dataset in S3                       | Dataset Module      | Integration Test    |
| FR-6   | Modify constraints                        | Constraints Module  | UI Test             |
| FR-7   | Toggle optional constraints               | Constraints Module  | UI Test             |
| FR-8   | Timeslot subdivision                      | Core Engine         | Functional Test     |
| FR-9   | Reset constraints                         | Constraints Module  | UI Test             |
| FR-10  | AI modifies constraints with confirmation | AI Agent            | Agent Test          |
| FR-11  | Generate timetable                        | Core Engine         | Performance Test    |
| FR-12  | Soft scoring system                       | Core Engine         | Algorithm Test      |
| FR-13  | ≤60 sec generation time                   | Core Engine         | Stress Test         |
| FR-14  | Detect conflicts                          | Core Engine         | Functional Test     |
| FR-15  | Regenerate timetable                      | Scheduler API       | Integration Test    |
| FR-16  | Natural-language interpretation           | AI Agent            | Agent Test          |
| FR-17  | Edit constraints via AI                   | AI Agent            | Tool-Call Test      |
| FR-18  | Detect dataset issues                     | AI Agent            | Agent Test          |
| FR-19  | Explain schedule                          | AI Agent            | Functional Test     |
| FR-20  | What-if simulations                       | AI Agent            | Scenario Test       |
| FR-23  | Multi-format exports                      | Export Module       | File Test           |
| FR-25  | Email/password login                      | Auth Module         | Security Test       |
| FR-27  | Free trial mode                           | Subscription Module | Billing Test        |
| FR-28  | Subscription validation                   | Subscription Module | Functional Test     |

---

# 18. Acceptance Criteria

These criteria determine whether ClassSync AI is ready for institutional deployment.

---

## 18.1 Functional Acceptance Criteria

### Dataset Upload

- System must accept CSV/XLSX for all mandatory datasets.
- Invalid datasets must trigger **clear error messages** and AI suggestions.
- Dataset completeness indicator must update in real-time.

### Constraints Configuration

- All constraints must be editable.
- Optional constraints must toggle correctly.
- Reset-to-default must restore factory values.

### Timetable Generation

- Must generate a **clash-free** timetable within **60 seconds** for:
  - 200 courses
  - 80 teachers
  - 60 rooms
- Hard constraints **must never** be violated.

### AI Agent

- Must interpret natural-language queries accurately.
- Must not modify constraints without confirmation.
- Must correctly run what-if scenarios and explain results.
- Must detect dataset inconsistencies.

### Exports

- All export formats (XLSX, CSV, PDF, PNG, ZIP) must match the generated schedule.
- Viewer must display timetable clearly with filters and drill-down options.

### Authentication & Subscription

- Users must log in using email/password.
- Subscription/Free Trial must control access to timetable generation.

---

## 18.2 Non-Functional Acceptance Criteria

### Performance

- Backend response time < 300ms (non-scheduling operations).
- UI loads < 2 seconds.
- AI responses < 5 seconds.

### Security

- All communication over HTTPS.
- Passwords stored securely (bcrypt/Argon2).
- Tenant isolation strictly enforced.

### Reliability

- System must auto-recover or log detailed errors.
- No data corruption after failed scheduling runs.

### Usability

- A new user must be able to generate a timetable in < 20 minutes with minimal guidance.

---

# 19. Project Risks & Mitigation Strategies

This section identifies technical, business, and user risks.

---

## 19.1 Technical Risks

### **R-1: AI Hallucination**

**Risk:** Incorrect suggestions or misleading information from AI.**Mitigation:**

- Strict tool-calling
- Confirmation prompts
- Logging all AI actions

---

### **R-2: Slow Scheduling Performance**

**Risk:** Large datasets may exceed 60s target.**Mitigation:**

- Optimization algorithm refinement
- Parallel computation strategies
- Caching and pre-validation

---

### **R-3: Dependency on LLM Providers**

**Risk:** LLM downtime impacts AI features.**Mitigation:**

- Secondary provider fallback (Gemini)
- Graceful failure modes

---

## 19.2 Business Risks

### **R-4: University Resistance to SaaS**

**Mitigation:**

- Offer API-only enterprise plan later
- Provide strong privacy guarantees
- Emphasize AI refinement value

---

### **R-5: Competitors copying the concept**

**Mitigation:**

- Python code obfuscation
- Proprietary scheduling logic
- Brand and academic partnerships

---

## 19.3 User Risks

### **R-6: Misconfigured Constraints**

**Mitigation:**

- AI-assisted configuration
- Reset-to-default
- Warning messages

---

### **R-7: Bad Input Data**

**Mitigation:**

- Field-by-field validation
- AI-assisted correction
- Template downloads

---

# 20. Assumptions & Dependencies

---

## 20.1 Assumptions

- Institutions will provide properly structured CSV/XLSX files.
- All users have stable internet access.
- Cloud infrastructure remains functional.
- LLM providers maintain availability.
- Browser compatibility remains current.

---

## 20.2 Dependencies

- OpenAI GPT-4.1 / Gemini 2.0 APIs
- FastAPI backend
- React-based frontend
- PostgreSQL database
- S3-compatible file storage
- Pandas, NumPy, OpenPyXL, ReportLab

---

# 21. Future Enhancements

These features are planned but not included in the current SRS version.

---

### **21.1 LMS Integration**

- Automatic publish to LMS (Moodle, Canvas, Blackboard).
- ICS calendar feed generation.

### **21.2 Teacher & Student Portals**

- Personalized timetable dashboards.
- Notification system (class changes, cancellations).

### **21.3 Predictive Scheduling**

- Predict future teacher load.
- Predict course demand distribution.

### **21.4 Mobile Apps (Android/iOS)**

- View timetables
- Push notifications

### **21.5 API Marketplace**

- Allow institutions to integrate external systems.

---

# 22. Final Conclusion

ClassSync AI is a modern, scalable, AI-enhanced timetabling system that addresses one of the most complex operational challenges in academic institutions.

With:

- A robust backend
- A powerful AI agent
- A modular scheduling engine
- A user-friendly interface
- Strict performance and security guarantees

ClassSync AI is positioned to become the leading academic scheduling solution.

This SRS fully defines the requirements necessary for development, testing, deployment, and future expansion.

---
