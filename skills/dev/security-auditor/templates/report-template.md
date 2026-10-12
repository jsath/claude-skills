# Security Audit Report

**Project:** {{PROJECT_NAME}}
**Date:** {{DATE}}
**Scan Depth:** {{SCAN_DEPTH}}
**Auditor:** {{AUDITOR}} (AI-assisted review, human verified)
**Stages completed:** {{STAGES_COMPLETED}}

---

## Executive Summary

{{EXECUTIVE_SUMMARY}}

### Risk Score: {{RISK_SCORE}}/10

| Severity | Count |
|----------|-------|
| Critical | {{CRITICAL_COUNT}} |
| High | {{HIGH_COUNT}} |
| Medium | {{MEDIUM_COUNT}} |
| Low | {{LOW_COUNT}} |
| Info | {{INFO_COUNT}} |
| **Total** | **{{TOTAL_COUNT}}** |

---

## Threat Model Overview

{{THREAT_MODEL_SUMMARY}}

---

## Findings Summary

| # | Severity | Category | Title | File | CVSS |
|---|----------|----------|-------|------|------|
{{FINDINGS_TABLE}}

---

## Detailed Findings

{{DETAILED_FINDINGS}}

---

## Dependency Audit

{{DEPENDENCY_FINDINGS}}

---

## Secrets Scan

{{SECRETS_FINDINGS}}

---

## Remediation Roadmap

### Immediate (Fix within 24-48 hours)
{{REMEDIATION_CRITICAL}}

### Short-term (Fix within 1-2 weeks)
{{REMEDIATION_HIGH}}

### Medium-term (Fix within 1-3 months)
{{REMEDIATION_MEDIUM}}

### Long-term (Best practices to adopt)
{{REMEDIATION_LOW}}

---

## Statistics

- **Files Scanned:** {{FILES_SCANNED}}
- **Lines of Code:** {{LINES_OF_CODE}}
- **Time Elapsed:** {{TIME_ELAPSED}}
- **Tech Stack:** {{TECH_STACK}}

## Coverage and limits

{{COVERAGE_AND_LIMITS}}

(State which stages ran, which tools were missing, files and lines actually reviewed, and what was not checked. A finding count of zero means zero in the reviewed scope only.)
