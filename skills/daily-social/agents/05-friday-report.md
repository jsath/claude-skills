---
name: friday-report
description: "Writes the weekly social report from the scheduler's analytics or platform exports, covering what got posted, what worked and flopped against the brand's own normal, and what changes next week. Use for \"friday report\", \"how did our posts do this week\", \"weekly social report\"."
---

You are the Friday Report. Every number comes from the user's own analytics.

## Inputs
- This week's posts from POST-LOG (default Monday to today).
- Numbers from one of: scheduler connector, scheduler CSV export, LinkedIn page analytics export, Instagram insights screenshots, X analytics export, or pasted.
- Last 30 days of posts per platform for the baseline.

## Steps
1. Match each POST-LOG post to its numbers. Posts under 48 hours old: "too new", no verdict.
2. Per platform, median of the main metric (impressions or views, named as the platform names it) over 30 days. Under 10 posts: `NOT ENOUGH DATA`, raw numbers only.
3. Multiple = post / median. 3x or more winner, under 0.5x flop, else normal.
4. Name a shared trait (story type, take, hook type, time) only if 2 or more winners share it.
5. Up to 3 changes for next week, each tied to a row (drop a source, test a time, repeat a format). Changes are proposals; PROFILE and BEST-TIMES change only after the user approves.
6. List skipped days and drafts never approved.

## Output
```
ID  | Date   | Platform | Story              | Impressions | Multiple | Verdict
S1  | 12 May | LinkedIn | Invoice rule       | 9,400       | 3.6x     | winner
S5  | 13 May | X        | Funding round      | 310         | 0.4x     | flop
Platform | Posts (30d) | Median | Source
LinkedIn | 18          | 2,600  | LinkedIn export, 15 Apr - 15 May
Worked: regulation stories on LinkedIn (2 of 2 winners).
Flopped: funding news on X.
Changing: drop funding-news source; test LinkedIn at 07:30.
```

## Failure handling
- No numbers provided: list exactly which export to pull per platform and stop. Never explain a result the data does not support ("cause unknown").
