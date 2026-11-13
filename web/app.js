'use strict';
// The PC does the thinking (/api/state arrives ready to paint); this file only paints,
// rotates panels and keeps the clock running even when the PC is gone.

const POLL_MS = 30000;
const POLL_TIMEOUT_MS = 10000;
const FALLBACK_OFFLINE = { es: 'sin conexión', en: 'offline' };
const FADE_MS = 1000; // a bit longer than the .9s fade in styles.css

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const $ = (id) => document.getElementById(id);
const pinned = new URLSearchParams(location.search).get('panel');

let state = null;
let panels = ['clock'];
let current = 'clock';
let timer = null;

const lang = () => (state ? state.lang : navigator.language.slice(0, 2) === 'es' ? 'es' : 'en');
const pad = (n) => String(n).padStart(2, '0');

function t(key, vars = {}) {
  let s = (state && state.strings[key]) || '';
  for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, v);
  return s;
}

// ---------- data ----------
async function poll() {
  const ctl = new AbortController();
  const timeout = setTimeout(() => ctl.abort(), POLL_TIMEOUT_MS);
  try {
    const res = await fetch('/api/state', { cache: 'no-store', signal: ctl.signal });
    if (!res.ok) throw new Error(res.status);
    state = await res.json();
    setOffline(false);
    render();
  } catch (e) {
    setOffline(true); // keep the last data on screen; the clock keeps going
  } finally {
    clearTimeout(timeout);
  }
}

function setOffline(offline) {
  document.body.classList.toggle('offline', offline);
  const text = offline
    ? (state ? t('offline') : FALLBACK_OFFLINE[lang()])
    : t(state.link === 'usb' ? 'link_usb' : 'link_wifi');
  $('link').textContent = text;
  $('offline-note').textContent = offline ? text : '';
  $('offline-note').className = offline ? 'offline-note link' : 'offline-note';
}

const renderers = {
  clock(s) {
    const w = s.clock.weather;
    $('weather').hidden = !w;
    if (!w) return;
    const icon = ['clear', 'partly_cloudy'].includes(w.condition) ? `${w.condition}-${w.is_day ? 'day' : 'night'}` : w.condition;
    $('weather-icon').setAttribute('href', `#${icon}`);
    $('weather-temp').textContent = `${w.temp}°`;
    $('weather-sky').textContent = `${w.label} · ${w.max}° / ${w.min}°`;
  },
};

renderers.github = (s) => {
  const g = s.github;
  const num = new Intl.NumberFormat(s.lang);
  const month = new Intl.DateTimeFormat(s.lang, { month: 'short' });
  $('gh-title').textContent = t('github_title');
  $('gh-total').textContent = num.format(g.total);
  $('gh-total-label').textContent = t('github_total');
  $('gh-streak').textContent = num.format(g.streak);
  $('gh-streak-label').textContent = t('github_streak');
  $('gh-today').textContent = num.format(g.today);
  $('gh-today-label').textContent = t('github_today');
  $('gh-less').textContent = t('github_less');
  $('gh-more').textContent = t('github_more');
  $('github').style.setProperty('--weeks', g.weeks.length);
  $('gh-months').innerHTML = g.months
    .map((m) => `<span style="grid-column:${m.week + 1}">${month.format(new Date(2000, m.month - 1, 1)).replace('.', '')}</span>`)
    .join('');
  $('gh-grid').innerHTML = g.weeks
    .map((week) => week.map((l) => (l === null ? '<i class="pad"></i>' : `<i class="l${l}"></i>`)).join(''))
    .join('');
};

renderers.claude = (s) => {
  const c = s.claude;
  $('claude-title').textContent = t('claude_title');
  $('claude-session-label').textContent = t('claude_session');
  $('claude-week-label').textContent = t('claude_week');
  for (const [name, w] of [['session', c.session], ['week', c.week]]) {
    $(`claude-${name}`).hidden = !w;
    if (!w) continue;
    $(`claude-${name}-pct`).textContent = w.pct;
    $(`claude-${name}-fill`).style.setProperty('--v', `${Math.min(w.pct, 100)}%`);
  }
  const pace = c.week && c.week.elapsed_pct !== null;
  $('claude-week-pace').hidden = !pace;
  $('claude-week-pace-note').hidden = !pace;
  if (pace) {
    $('claude-week-pace').style.setProperty('--v', `${c.week.elapsed_pct}%`);
    $('claude-week-elapsed').textContent = t('claude_week_elapsed', { pct: c.week.elapsed_pct });
  }
  claudeNotes(new Date());
};

// Reset notes count down on the phone, so they stay right even if the PC goes away.
function claudeNotes(now) {
  const c = state && state.claude;
  if (!c) return;
  if (c.session) {
    const at = c.session.resets_at && new Date(c.session.resets_at);
    $('claude-session-note').textContent = at && at > now ? t('claude_resets_in', { duration: duration(at - now) }) : '';
  }
  if (c.week) {
    const at = c.week.resets_at && new Date(c.week.resets_at);
    $('claude-week-note').textContent = at && at > now
      ? t('claude_resets_on', {
          weekday: new Intl.DateTimeFormat(state.lang, { weekday: 'long' }).format(at),
          time: new Intl.DateTimeFormat(state.lang, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(at),
        })
      : '';
  }
}

function duration(ms) {
  const minutes = Math.ceil(ms / 60000);
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? t('duration_hm', { h, m }) : t('duration_m', { m });
}

// ---------- photos ----------
let photoIndex = -1;
let photoReady = null;

// Decode the next photo before its panel shows, so it fades in whole.
async function preparePhoto() {
  const list = (state && state.photos) || [];
  if (!list.length) return false;
  photoIndex = (photoIndex + 1) % list.length;
  // Decode the very <img> elements that get shown; a separate Image() would be decoded twice.
  const main = $('photo-main');
  const back = $('photo-back');
  main.src = back.src = list[photoIndex];
  try {
    await main.decode();
    const portrait = main.naturalHeight > main.naturalWidth;
    $('photos').classList.toggle('portrait', portrait);
    if (portrait) await back.decode();
  } catch (e) {
    return false;
  }
  return true;
}

function render() {
  document.documentElement.lang = state.lang;
  for (const id of state.panels) if (renderers[id]) renderers[id](state);
  setPanels(state.panels);
  tick();
}

// ---------- rotation ----------
function setPanels(list) {
  const next = pinned && list.includes(pinned) ? [pinned] : list;
  if (next.join() === panels.join()) return;
  panels = next;
  $('progress').innerHTML = panels.length > 1 ? panels.map(() => '<span><i></i></span>').join('') : '';
  // Staying on the same panel must not reload it (a photo on screen would jump).
  if (panels.includes(current)) show(current);
  else go(panels[0]);
}

async function go(id) {
  if (id === 'photos') {
    const ok = await (photoReady || preparePhoto());
    photoReady = null;
    // A photo that won't load skips its turn instead of showing an empty panel.
    if (!ok && panels.length > 1) id = panels[(panels.indexOf('photos') + 1) % panels.length];
  }
  show(id);
}

function show(id) {
  current = id;
  for (const p of document.querySelectorAll('.panel')) p.classList.toggle('on', p.id === id);
  document.body.dataset.panel = id;
  const k = panels.indexOf(id);
  [...$('progress').children].forEach((s, i) => {
    s.className = i < k ? 'done' : '';
    if (i === k) { void s.offsetWidth; s.className = 'run'; }
  });
  clearTimeout(timer);
  document.documentElement.style.setProperty('--dwell', dwell() + 'ms');
  if (panels.length > 1) {
    const following = panels[(k + 1) % panels.length];
    // Swap the photo only after the photos panel has finished fading out.
    if (following === 'photos' && id !== 'photos') photoReady = wait(FADE_MS).then(preparePhoto);
    timer = setTimeout(next, dwell());
  }
}

function dwell() {
  return (state ? state.seconds_per_panel : 15) * 1000;
}

function next() {
  go(panels[(panels.indexOf(current) + 1) % panels.length]);
}

// ---------- clock ----------
const tickers = [claudeNotes];

function tick() {
  const d = new Date();
  $('hh').textContent = pad(d.getHours());
  $('mm').textContent = pad(d.getMinutes());
  $('corner-time').textContent = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  $('wd').textContent = new Intl.DateTimeFormat(lang(), { weekday: 'long' }).format(d);
  $('dm').textContent = new Intl.DateTimeFormat(lang(), { day: 'numeric', month: 'long' }).format(d);
  for (const f of tickers) f(d);
}

// ---------- start ----------
// The icon sprite goes inline: <use> pointing at another file didn't render reliably.
fetch('weather-icons.svg')
  .then((r) => r.text())
  .then((svg) => document.body.insertAdjacentHTML('afterbegin', svg))
  .catch(() => {});
tick();
setInterval(tick, 1000);
poll();
setInterval(poll, POLL_MS);

// Tap: next panel. The app keeps the page full screen and turns the screen on and off.
document.addEventListener('click', () => {
  if (panels.length > 1) next();
});
