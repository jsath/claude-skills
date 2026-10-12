# Worked example (fictional)

Everyone and everything here is made up.

## Input

The user (Sam Lee, sam@brightpath.example) pastes call notes and the invite, and says: "Follow up on yesterday's Northwind call. Cooldown 3 business days."

Invite: "Northwind x Brightpath: reporting pilot", Tue 6 Oct, 10:00-10:45 America/New_York. Organizer sam@brightpath.example. Invitees: dana@northwind.example (accepted), luis@northwind.example (no response), priya@brightpath.example (accepted).

Notes (excerpt):

> Dana: we want the pilot live before the quarter closes. Luis does the weekly report by hand, about four hours.
> Sam: I'll send the pilot outline and a sample report by Thursday.
> Dana: I'll get you last month's export. Our IT lead, Marco, has to approve access.
> Priya: I can do a 20 minute walkthrough with Luis next week.

Email check: Luis replied on 7 Oct, "Happy to do Tuesday 13 Oct 2pm." A calendar event for 13 Oct with Luis and Priya exists. No outline sent yet.

## Output (shortened)

**Bottom line:** 3 actions. The outline and sample report are owed by us and go today. The walkthrough is already booked. Marco's email is unknown.

**Attendees**

| Name | Email | Role | Attended? | Source |
|---|---|---|---|---|
| Dana | dana@northwind.example | Sponsor, wants pilot this quarter | yes | invite, transcript |
| Luis | luis@northwind.example | Does the weekly report | unknown (mentioned, does not speak) | invite, transcript |
| Marco | UNVERIFIED: ask user | IT lead, approves access | not invited | transcript only |
| Priya | priya@brightpath.example | Our side, walkthrough | yes | invite, transcript |

**Promises**

| # | What | Owed by | Evidence |
|---|---|---|---|
| P1 | Pilot outline + sample report by Thu 8 Oct | us (Sam) | "I'll send ... by Thursday" |
| P2 | Last month's export | them (Dana) | "I'll get you last month's export" |
| P3 | IT access approval | them (Marco) | "Marco has to approve access" |
| P4 | Walkthrough with Luis | us (Priya) | "20 minute walkthrough" |

**Recommendations**

| # | Action | Covers | Owner | To | CC | Status |
|---|---|---|---|---|---|---|
| A1 | Send outline + sample, ask for export and Marco's contact | P1, P2, P3 | Sam | Dana | Luis | SEND NOW |
| A2 | Walkthrough | P4 | Priya | n/a | n/a | NO ACTION (booked 13 Oct) |
| A3 | Access request to Marco | P3 | Sam | Marco | Dana | NEEDS INFO (Marco's email) |

P2 and P3 ride on A1 because they share Dana's thread: one action, not three.

**Draft A1**

To: dana@northwind.example | CC: luis@northwind.example | Reply in "Northwind x Brightpath: reporting pilot"

> Hi Dana,
>
> As promised, here is the pilot outline and a sample report built on the weekly format Luis described. [ATTACH: pilot outline] [ATTACH: sample report]
>
> Two things from your side would keep us on track for this quarter: last month's export, and an intro to Marco so we can start the access approval.
>
> Priya and Luis are set for Tuesday at 2pm.
>
> Sam

**Gaps:** Marco's email (ask Dana). Luis: invited, RSVP blank, not heard in the notes; ask Sam whether he joined.

Nothing was sent, scheduled or changed. Drafts are for your review.
