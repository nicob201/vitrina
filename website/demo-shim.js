// Injected into dist/demo/index.html before app.js. The demo is the real page (web/), but there is no server:
// this answers /api/state and /api/metrics in the browser, with sample data that is always relative to the visitor's "now".
(() => {
  const DAY = 86400000;
  const HOUR = 3600000;
  const lang = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'es';
  const t0 = Date.now(); // the reset times hang from page load, so the countdowns really count down
  const realFetch = window.fetch.bind(window);
  const pinned = new URLSearchParams(location.search).get('panel');
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

  // Tell the site the demo can be shown: for a pinned panel, once app.js has switched to it and its 0.9 s fade is over.
  function announceReady() {
    if (announced || window.parent === window) return;
    announced = true;
    const tell = (delay) => setTimeout(() => window.parent.postMessage({ vitrinaDemo: 'ready' }, location.origin), delay);
    if (!pinned || pinned === 'clock') return tell(400); // the clock is on from the start
    const body = document.body;
    const check = () => {
      if (body.dataset.panel !== pinned) return;
      observer.disconnect();
      tell(1000);
    };
    const observer = new MutationObserver(check);
    observer.observe(body, { attributes: true, attributeFilter: ['data-panel'] });
    check();
  }

  async function demoState() {
    if (!loaded) {
      loaded = Promise.all([
        realFetch(`state.${lang}.json`).then((r) => r.json()),
        realFetch('demo-days.json').then((r) => r.json()),
      ]);
    }
    let base, pairs;
    try {
      [base, pairs] = await loaded;
    } catch (e) {
      loaded = null; // a failed first load must not stick: the next poll tries again
      throw e;
    }
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
    announceReady();
    return json(state);
  }

  // The shape of vitrina/metrics.py::Metrics.body, with made-up curves. Each sample depends only on its own
  // time, so the history scrolls to the left on every request, like a real one.
  function demoMetrics(now) {
    const GIB = 2 ** 30;
    const last = Math.floor(now / 5000) * 5;
    const samples = [];
    for (let t = last - 295; t <= last; t += 5) {
      const wave = (period, shift) => (Math.sin((t / period) * 2 * Math.PI + shift) + 1) / 2; // 0..1
      const burst = wave(140, 1) ** 6; // now and then something gets busy
      samples.push({
        t,
        cpu: round(12 + 14 * wave(47, 0) + 8 * wave(19, 2) + 40 * burst),
        gpu: round(4 + 9 * wave(71, 3) + 25 * burst),
        ram: round((13.4 + 1.2 * wave(260, 0) + 0.2 * wave(33, 1)) * GIB),
        down: round(1e5 + 5e5 * wave(29, 4) + 3.5e6 * wave(110, 2) ** 8),
        up: round(2e4 + 9e4 * wave(37, 5) + 4e5 * burst),
      });
    }
    return {
      interval: 5,
      samples,
      ram_total: 24 * GIB,
      disk: { free: 302e9, total: 494e9 },
      battery: { pct: 80, state: 'ac' },
    };
  }

  const json = (body) => new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });

  window.fetch = (input, init) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.href);
    if (url.pathname === '/api/state') return demoState();
    if (url.pathname === '/api/metrics') return Promise.resolve(json(demoMetrics(Date.now())));
    return realFetch(input, init);
  };
})();
