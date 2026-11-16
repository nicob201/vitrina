// Injected into dist/demo/index.html before app.js. The demo is the real page (web/), but there is no server:
// this answers /api/state in the browser, with sample data that is always relative to the visitor's "now".
(() => {
  const DAY = 86400000;
  const HOUR = 3600000;
  const lang = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'es';
  const t0 = Date.now(); // the reset times hang from page load, so the countdowns really count down
  const realFetch = window.fetch.bind(window);
  let loaded = null;
  let announced = false;

  // Port of vitrina/github.py::github_view. pairs: 365 [level, count], oldest first, the last one is today.
  function githubView(pairs, todayMs) {
    const days = pairs.map(([level, count], i) => ({ ms: todayMs - (364 - i) * DAY, level, count }));
    const counts = new Map(days.map((d) => [d.ms, d.count]));
    let streak = 0;
    let day = counts.get(todayMs) ? todayMs : todayMs - DAY; // today isn't over yet
    while ((counts.get(day) || 0) > 0) { streak++; day -= DAY; }
    const weeks = [];
    const firstOfWeek = new Map();
    const start = days[0].ms - new Date(days[0].ms).getUTCDay() * DAY; // the Sunday that opens the first week
    for (const d of days) {
      const diff = Math.round((d.ms - start) / DAY);
      const w = Math.floor(diff / 7);
      const slot = diff % 7;
      while (weeks.length <= w) weeks.push([]);
      while (weeks[w].length < slot) weeks[w].push(null);
      weeks[w].push(d.level);
      if (!firstOfWeek.has(w)) firstOfWeek.set(w, d.ms);
    }
    const months = [];
    for (const w of [...firstOfWeek.keys()].sort((a, b) => a - b)) {
      const month = new Date(firstOfWeek.get(w)).getUTCMonth() + 1;
      if (!months.length || months[months.length - 1].month !== month) months.push({ week: w, month });
    }
    if (months.length > 1 && months[0].week === 0 && months[1].week <= 2) months.shift(); // a sliver would crowd the next label
    return {
      total: days.reduce((n, d) => n + d.count, 0),
      streak,
      today: counts.get(todayMs) || 0,
      weeks,
      months,
    };
  }

  window.__demoGithubView = (pairs, iso) => githubView(pairs, Date.parse(iso + 'T00:00:00Z'));

  // Port of vitrina/claude.py::claude_view for the two sample windows.
  const round = (x) => Math.floor(x + 0.5);
  function windowView(pct, resetsMs, now, isWeek) {
    if (now >= resetsMs) return isWeek ? { pct: 0, resets_at: null, elapsed_pct: null } : { pct: 0, resets_at: null };
    const view = { pct, resets_at: new Date(resetsMs).toISOString() };
    if (isWeek) {
      const elapsed = ((now - (resetsMs - 7 * DAY)) / (7 * DAY)) * 100;
      view.elapsed_pct = round(Math.min(Math.max(elapsed, 0), 100));
    }
    return view;
  }

  async function demoState() {
    loaded = loaded || Promise.all([
      realFetch(`state.${lang}.json`).then((r) => r.json()),
      realFetch('demo-days.json').then((r) => r.json()),
    ]);
    const [base, pairs] = await loaded;
    const now = Date.now();
    const d = new Date(now);
    const todayMs = Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()); // the visitor's calendar day
    const state = Object.assign({}, base, {
      github: githubView(pairs, todayMs),
      claude: {
        session: windowView(42, t0 + (2 * 60 + 14) * 60000, now, false),
        week: windowView(51, t0 + (3 * 24 + 5) * HOUR, now, true),
      },
    });
    if (!announced && window.parent !== window) {
      announced = true;
      setTimeout(() => window.parent.postMessage({ vitrinaDemo: 'ready' }, location.origin), 400);
    }
    return new Response(JSON.stringify(state), { headers: { 'Content-Type': 'application/json' } });
  }

  window.fetch = (input, init) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.href);
    return url.pathname === '/api/state' ? demoState() : realFetch(input, init);
  };
})();
