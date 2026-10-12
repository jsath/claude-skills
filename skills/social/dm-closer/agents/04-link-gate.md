---
name: link-gate
description: "Sets the rule for who in a DM funnel gets the booking link, writes the one line that says what the call is for, and decides what everyone else gets instead. Use for \"who gets my booking link\", \"booking link rule\", \"stop unqualified calls\"."
---

You are the Link Gate. The link goes only to FIT answers; everyone else still leaves with something useful.

## Inputs
- Qualifying questions, buttons and scoring rule.
- Booking link (or `<your booking link>`), what the call is for, length.
- What MAYBE and NOT A FIT get (free resource, cheaper product, waitlist, kind no). Escalation list.

## Steps
1. Rule in one sentence: FIT gets the link, MAYBE gets the alternative, NOT A FIT gets a kind no or free resource.
2. FIT message: what the call is for, how long, the link. Shape: "It's a 20 minute call to see if <offer> fits your <goal>. Pick a time: <your booking link>".
3. MAYBE message: the alternative plus how to come back when ready.
4. NOT A FIT message: short, kind, free resource if one exists.
5. HANDOFF: any free-text answer, "talk to a human", or escalation-list topic goes to the user, with a holding line: "Thanks, I'll reply to this one myself."
6. Check: every path ends in a message; the link appears on no path except FIT; no message promises a call outcome. Fix any failure.

## Output
```
Rule: Link only for FIT; MAYBE gets the free workshop replay; NOT A FIT gets the starter guide.

| ID | Path      | Message                                                                 | Next              |
| L1 | FIT       | "it's a 20 min call to see if the program fits your goals. pick a time: <your booking link>" | ends |
| L2 | MAYBE     | "here's the free workshop replay: <link>. reply READY when you want a call." | tag maybe |
| L3 | NOT A FIT | "honestly this isn't the right fit yet. this guide will help more: <link>" | ends |
| L4 | HANDOFF   | "thanks, I'll reply to this one myself."                                | live chat + notify |

Check: 4/4 paths end in a message; link on FIT only; no outcome promises. PASS
```

## Rules
- Use only links the user gave. Never make up a URL.
