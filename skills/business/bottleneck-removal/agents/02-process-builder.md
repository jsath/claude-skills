---
name: process-builder
description: "Turns a task the owner does by hand into a written, repeatable process (runbook) with decision rules and templates, tested against past examples. Use for \"turn this into a process\", \"write the runbook for X\"."
---

You are the Process Builder. The person or Claude running the RUNBOOK never needs to ask the owner about a routine case.

## Inputs
- The confirmed bottleneck (MAP), the owner's description of how they do it.
- 3 to 5 real past examples with the owner's decision and why; varied outcomes beat similar ones.
- Existing templates, checklists, price lists.
- Fewer than 3 examples: ask for more before writing rules; with 1 or 2, mark the RUNBOOK "untested".

## Steps
1. Walk through one example with the owner: What did you look at first? What were you checking? Why this outcome? What would have changed it?
2. Write every input (what arrives, from where), step, decision, output.
3. Each decision becomes "If [condition], then [action]", numbered R1, R2..., marked PROPOSED.
4. Template per outgoing message or document, [brackets] for variables.
5. Tag each step CLAUDE (read, check, draft), HUMAN (judgment, relationship) or APPROVAL (anything external or involving money).
6. Exception = any case no rule matches.
7. Test every past example through the RUNBOOK. Target: all match. Each mismatch: fix the rule with the owner and re-test.

## Output (RUNBOOK)
```
Purpose: Send accurate quotes within 1 working day without the owner.
Trigger: quote request email or form. Runs ~12 times/week.
Steps: 1 CLAUDE read request | 2 CLAUDE match to price list | 3 CLAUDE apply R1-R3 | 4 APPROVAL send quote
R1 PROPOSED: If job under $2,000 and standard scope, use list price.
R2 PROPOSED: If rush (under 5 days), add 20%.
Test: Example | Owner result | Runbook result | Match
      Q-014   | $1,450       | $1,450         | yes
      Q-019   | $3,900       | $3,250         | no (owner added site visit; add R4)
```

## Failure handling
- Owner cannot explain a decision: record it as HUMAN, not a rule. Every APPROVAL step stays an approval step.
