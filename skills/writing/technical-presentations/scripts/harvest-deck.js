// harvest-deck.js: collect every slide's visible text, speaker notes and timing
// from a live HTML deck (reactive web app). Read-only.
//
// Use: open the deck at its FIRST slide, open notes if they toggle, then paste
// this into the browser console. Or with Playwright:
//   const slides = await page.evaluate(require('fs').readFileSync('harvest-deck.js', 'utf8'));
//
// Adapt the four selectors below to the app. Afterwards confirm that counters
// are consecutive and titles differ: a loop can silently capture slide 1 N times
// if the app renders after the click returns (raise RENDER_WAIT_MS if so).
(async () => {
  const SLIDE_SEL = 'article, section.slide, .slide.active';
  const NOTES_SEL = 'aside.notes p, .notes p, .speaker-notes';
  const TIME_SEL = '.slide-time, [data-time]';
  const NEXT_SEL = 'button[aria-label="Next slide"], [data-go="next"], .next';
  const RENDER_WAIT_MS = 60;

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const counter = () => {
    const m = document.body.innerText.match(/\b(\d+)\s*\/\s*(\d+)\b/);
    return m ? { current: Number(m[1]), total: Number(m[2]) } : null;
  };

  const start = counter();
  const total = start ? start.total : 200;
  const out = [];
  let previousText = null;

  for (let i = 0; i < total; i++) {
    await sleep(RENDER_WAIT_MS);
    const slide = document.querySelector(SLIDE_SEL);
    if (!slide) break;
    const text = slide.innerText || '';
    const rect = slide.getBoundingClientRect();
    out.push({
      n: i + 1,
      displayed: counter() ? counter().current : null,
      url: location.href,
      id: slide.getAttribute('data-id') || slide.id || null,
      text,
      notes: [...document.querySelectorAll(NOTES_SEL)].map((e) => e.innerText).join('\n'),
      time: (slide.querySelector(TIME_SEL) || {}).innerText || '',
      overflows: slide.scrollHeight > slide.clientHeight + 2 || rect.bottom > window.innerHeight,
      sameAsPrevious: text === previousText,
    });
    previousText = text;
    const next = document.querySelector(NEXT_SEL);
    if (!next) break;
    next.click();
  }

  const repeats = out.filter((s) => s.sameAsPrevious).length;
  console.log(`harvested ${out.length} slides, ${repeats} identical to the previous one (check render wait if > 0)`);
  return out;
})();
