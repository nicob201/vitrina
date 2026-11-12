'use strict';
// The PC does the thinking (/api/state arrives ready to paint); this file only paints,
// rotates panels and keeps the clock running even when the PC is gone.

const POLL_MS = 30000;
const POLL_TIMEOUT_MS = 10000;
const FALLBACK_OFFLINE = { es: 'sin conexión', en: 'offline' };

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
  show(panels.includes(current) ? current : panels[0]);
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
  if (panels.length > 1) timer = setTimeout(next, dwell());
}

function dwell() {
  return (state ? state.seconds_per_panel : 15) * 1000;
}

function next() {
  show(panels[(panels.indexOf(current) + 1) % panels.length]);
}

// ---------- clock ----------
const tickers = [];

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

// Tap: next panel. In a plain browser also go full screen and keep the screen on.
document.addEventListener('click', () => {
  if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
    document.documentElement.requestFullscreen().catch(() => {});
  }
  if (navigator.wakeLock) navigator.wakeLock.request('screen').catch(() => {});
  if (panels.length > 1) next();
});
