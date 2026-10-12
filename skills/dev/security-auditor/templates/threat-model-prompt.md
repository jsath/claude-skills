# Threat Model Generation Prompt

You are an expert application security architect. Analyze the following codebase information and produce a comprehensive threat model.

## Project Information

**Tech Stack:** {{TECH_STACK}}
**Framework:** {{FRAMEWORK}}
**Project Structure:**
```
{{FILE_TREE}}
```

**Key Configuration Files:**
```
{{CONFIG_FILES_CONTENT}}
```

## Instructions

Generate a threat model covering:

### 1. Security Objectives
- What data does this application handle?
- What are the confidentiality, integrity, and availability requirements?
- What compliance requirements might apply (GDPR, SOC2, HIPAA, PCI-DSS)?

### 2. Attack Surface Analysis
- **Entry Points**: All HTTP endpoints, API routes, WebSocket connections, CLI interfaces
- **External Integrations**: Third-party APIs, databases, message queues, file storage
- **Authentication Boundaries**: Where auth is required vs public access
- **Data Flow**: How sensitive data moves through the system (input → processing → storage → output)

### 3. Threat Actors
- Unauthenticated external attacker
- Authenticated regular user (privilege escalation)
- Malicious insider
- Supply chain attacker (compromised dependency)

### 4. STRIDE Analysis
For each major component, analyze:
- **S**poofing: Can identity be faked?
- **T**ampering: Can data be modified in transit/at rest?
- **R**epudiation: Can actions be denied without audit trail?
- **I**nformation Disclosure: Can sensitive data leak?
- **D**enial of Service: Can the service be overwhelmed?
- **E**levation of Privilege: Can users gain unauthorized access?

### 5. High-Risk Areas
Based on the tech stack, identify the top 5 areas most likely to contain vulnerabilities.

### Output Format
Use markdown with clear headings. Be specific: reference actual files and routes from the project structure. Don't be generic.
