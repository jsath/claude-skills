# Reviewing generated compliance policies (SOC 2, ISO 27001 drafts)

Use when a compliance platform (Vanta, Drata, Sprinto, Secureframe or similar)
has generated a policy set and someone wants to approve it.

Never recommend bulk approval because the platform generated the documents. An
approved false statement creates audit exposure and is worse than an honestly
documented gap.

## Check every policy against six questions

| Question | What to verify | Typical fix |
|---|---|---|
| True today? | The systems, devices, identity provider, network, vendors and roles described actually exist | Delete boilerplate about offices, company laptops, internal networks or servers you do not have |
| Evidence path? | Each recurring claim has an artifact: MFA report, device inventory, access review, training record, backup test, vendor review, incident exercise | Name the artifact and where it lives, or downgrade the claim |
| Achievable frequency? | Monthly, quarterly and annual promises are realistic and on a calendar | Change cadence to what will really happen |
| Real owner? | Each named owner has accepted the duty; separation of duties is real | Remove separation-of-duties claims a small team cannot meet; document compensating controls |
| Policy matches procedure? | The policy says what is required; the procedure says how, with the actual tools | Rewrite the procedure around the real tools |
| Control state? | Approving a document does not fix a failing platform check | Track each failing control separately with an owner and date |

## Output

A table per policy: keep / edit / remove sections, the exact sentences that are
untrue today, the evidence artifact for each recurring control, and a separate
list of failing controls that need work regardless of wording.
