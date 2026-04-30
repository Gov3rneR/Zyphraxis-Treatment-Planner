# Zyphraxis — Privacy Policy

**Effective Date:** 2024-01-01  
**Version:** 1.0

---

## 1. What Data Zyphraxis Collects

Zyphraxis logs the following data during operation:

| Data Type | Where Stored | Purpose |
|---|---|---|
| Request parameters (escape window, mode, risk threshold) | `logs/zyphraxis.log` | Debugging, audit trail |
| Optional patient ID (if supplied by caller) | `logs/zyphraxis.log` | Request traceability |
| Engine outputs (plan, metrics, explanation) | `logs/zyphraxis.log` | Explainability and audit |
| Observed outcomes (if submitted via `/learn`) | `data/memory.json` | Model improvement research |
| Run statistics (total runs, no-path count) | `data/stats.json` | Operational monitoring |

**Zyphraxis does not collect** names, dates of birth, contact details, genetic data, or any other directly identifying patient information. The optional `patient_id` field is an opaque reference only — callers are responsible for ensuring it does not contain identifying information.

---

## 2. How Data Is Used

Logged data is used exclusively for:

- Debugging and diagnosing system errors
- Providing an audit trail for research reproducibility
- Improving the planning algorithm through outcome analysis

Data is **never** shared with third parties, used for commercial profiling, or transmitted outside the host environment.

---

## 3. Data Retention and Security

- Log files are rotated at 10 MB with five backups retained (configurable in `.env`)
- All data remains on the host system where Zyphraxis is deployed
- No data is transmitted to external servers by the Zyphraxis application itself
- Deployers are responsible for securing the host environment, access controls, and backup procedures

---

## 4. Your Obligations as Deployer

If you process any personal data through Zyphraxis (including pseudonymous patient identifiers), you are the **data controller** under applicable law (e.g. GDPR, HIPAA, DPDPA). You are responsible for:

- Obtaining appropriate consent or establishing a lawful basis for processing
- Implementing technical and organisational security measures
- Responding to data subject rights requests
- Notifying regulators of any data breaches within required timeframes

---

## 5. Changes to This Policy

This policy may be updated. The effective date above reflects the version in this repository. Deployers should review the policy before each major deployment.

---

## 6. Contact

For questions about data handling, contact the system administrator or research lead responsible for your Zyphraxis deployment.
