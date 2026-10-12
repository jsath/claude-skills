# Auditing a live HTML deck

Use when the deck is a web app. Inspect the live URL first and harvest every slide and speaker note before judging the narrative.

When the deck is a web app, inspect the authoritative live URL first. Do not review only the linked slide. Harvest every slide and every visible speaker note before judging the narrative.

Reactive decks often render after the click/event loop returns. A synchronous loop can silently capture the first slide repeatedly. Use the asynchronous probe in `scripts/harvest-deck.js` (paste into the browser console, or run it through Playwright `page.evaluate`). The core loop:

```js
(async () => {
  const out = [];
  const countText = document.body.innerText.match(/\b\d+\s*\/\s*(\d+)\b/);
  const total = countText ? Number(countText[1]) : 100;

  for (let i = 0; i < total; i++) {
    await new Promise(resolve => setTimeout(resolve, 25));

    const slide = document.querySelector('article');
    if (!slide) break;

    out.push({
      n: i + 1,
      text: slide.innerText || '',
      notes: document.querySelector('aside.notes p, .notes p')?.innerText || '',
      time: slide.querySelector('.slide-time')?.innerText || ''
    });

    const next = document.querySelector(
      'button[aria-label="Next slide"], [data-go="next"]'
    );
    if (!next) break;
    next.click();
  }

  return out;
})()
```

Adapt selectors and render delay to the app. Confirm that slide numbers or titles actually change; do not trust a loop merely because it returned the expected number of records. If notes are toggleable, open them before extraction.

### Auditing a requested slide range

When the user requests slides `N-M`, do not assume a `?slide=N` query renders displayed slide N. Many HTML decks use a zero-based route parameter while projecting one-based counters.

1. Navigate to both range boundaries and record the **displayed counter**, route/query value, and slide `data-id` or title.
2. Start extraction from the displayed slide, not from the URL number. Verify the collected counters are consecutive and the IDs/titles are distinct.
3. Preserve two separate content records:
   - **DOM reconstruction:** exact title, kicker, body, timing, notes, links, image/QR labels, and hidden or off-screen text present in the slide DOM.
   - **Projected reconstruction:** what is actually visible at the audited viewport, including clipping, overflow, overlap, below-fold copy, and controls obscuring content.
4. Label these explicitly when they differ. Do not call DOM text "visible copy" if visual inspection shows it outside the viewport.
5. Mechanically sum timing labels for the exact range, then separately estimate room time for audience prompts, demos, Q&A, QR scanning, typing, and network friction.
6. Record notes exactly and distinguish empty notes from notes that merely repeat projected copy.
7. Validate internal contradictions such as `four stages` with only three items, `no form` beside required contact fields, or a privacy promise contradicted by the interaction.

Then visually inspect representative slides from every section, including the densest slide, the demo slide, the conversion/QR slide, and at least one personalized slide. For a short requested range, inspect every distinct layout type and every unusually dense slide. Text extraction alone cannot judge room readability or visual monotony.

### Preserve two evidence ledgers for implementation handoffs

A dynamic deck often has two different authoritative representations. Harvest both instead of treating either as complete:

1. **Source-data ledger:** slide ID, declared title/body, section, layout key, speaker notes, embedded timing, and source asset URL. This is authoritative for timing and author-supplied metadata, even when timing is not projected.
2. **Projected-DOM ledger:** displayed counter, route value, complete `article.innerText`, diagram/card labels, links, images, element geometry, visibility, and viewport clipping. This is authoritative for what the room can actually see.

Do not call the slide `body` field the complete projected copy when visual generators add labels, cards, legends, or access text. Conversely, do not infer timing from the DOM when the app keeps timing only in bundled slide data.

For a durable audit package:

- save deployed JS/CSS asset URLs and exact downloaded assets;
- export both ledgers as JSON plus readable Markdown;
- record viewport dimensions and extraction timestamp;
- verify total slides, distinct IDs, consecutive counters, and first/last routes;
- mechanically sum embedded timings and state whether timing is actually projected;
- retain the live URL as the primary source and treat local assets as evidence snapshots only.

If browser-console extraction returns useful but unsavable or excessively large output, reproduce the same read-only pass with a local headless browser against the live URL. Use an available system browser and keep the extraction script in the evidence directory. This is a persistence technique, not a negative claim about browser tooling.

### Validate the revision brief itself

After writing an implementation-ready brief, run deterministic checks over the Markdown:

- expected revised-slide heading count and unique proposed IDs;
- one timing entry per revised slide and an arithmetic runtime total;
- presence of every user-mandated domain, integration, use case, and safety boundary;
- complete current-slide disposition coverage;
- zero matches for required-removal phrases outside sections that quote them as audit evidence;
- consistency between beat-level timing tables and slide-level timings.

A manually written timing table can be internally wrong even when its grand total is right. Recompute each beat from the slide-level timings before delivery.
