# Writing the reel script

The edit can be perfect and the video still reads as AI if the words are
wrong. This is the part that gets rejected most often.

## Beat structure

Roughly 140 to 155 words, landing 32 to 40 s at 3.8 to 4.0 words per second.

| beat | words | job |
|---|---|---|
| Hook | 7 to 18 | the first three words carry it |
| Setup + name + proof | ~40 | name the thing, one hard number |
| Mechanism A | ~25 | why it works, what it really is |
| Mechanism B | ~20 | what it literally does, in verbs |
| Payoff | ~35 | what the viewer gets |
| Price | 5 to 10 | "it's free", or the licence |
| CTA | ~8 | the comment keyword, said out loud |

## The hook: the first three words decide it

Openers that work, in order:

1. Second person: "Your AI agents..." The subject is something they own.
2. The product's own name when it sounds impossible: "Free Claude Code...".
3. A recognisable brand: "Cash App's parent...".

Weak first three words: a concept, a preamble, or "There". Never open with a
rhetorical question.

## Register: how not to sound like AI

The tells are not formality. They are performed style:

- **No "Not X. Y." antithesis.** "Not as a bot. As an actual member." The
  single most recognisable AI tell.
- **No performed asides.** "and yeah, that Block. Square, Cash App." Trying
  to sound offhand reads as more AI, not less.
- **No technical-writer register.** "the difference isn't cosmetic", "by a
  factor of forty", "is a signed event in one log".
- **No tacked-on trailing clauses.** "..., in the same place your team talks."
- **Raw numbers, never ratios.** "Their next biggest repo has 700" beats "by
  a factor of forty".
- **Concrete comparisons over jargon.** "you give it access the way you'd
  give a new hire access" beats "scoped by identity, not permission flags".
- **No em dashes or en dashes** in any script or caption. Use a period or a
  comma, or rewrite the line.

What works: plain declaratives, contractions, the occasional fragment for
emphasis, and one first-person judgement ("that matters because..."). Say the
thing and stop.

## Accuracy rules that bite

- **Write numbers as digits**: `2,000`, `700,000`. Whisper emits digits, so a
  script saying "seven hundred thousand" fails to align and captions drop words.
  Digits also read faster on screen.
- **Never claim a repo "launched today"** without checking `created_at`
  (`gh api repos/<owner>/<repo> --jq .created_at`). Trending is not new.
- **Attribute what you cannot verify**: "the README puts it at..." rather
  than asserting a vendor's number as fact.

## Before handing the script to the recorder

- [ ] 140 to 155 words, hook first three words pass the list above
- [ ] zero "Not X. Y." lines, zero em or en dashes
- [ ] every number written as digits, each with a source path or URL in a notes file
- [ ] the CTA keyword is said out loud and matches the post caption (see `reel-captions`)
