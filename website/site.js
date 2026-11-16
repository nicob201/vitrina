// The page works in Spanish without this file (except the demo); this adds English, the copy buttons,
// the screen scaling and the demo's fade-in. Strings are our own constants, so innerHTML is safe here.
const REPO = 'https://github.com/nicob201/vitrina';
const link = (href, text) => `<a href="${href}" rel="noopener noreferrer">${text}</a>`;

const STRINGS = {
  es: {
    'meta.title': 'vitrina — tu celu viejo, ahora una pantalla de escritorio',
    'meta.description': 'Convertí un Android viejo en una mini pantalla de escritorio con la hora, el clima, tu actividad en GitHub, el uso de Claude y tus fotos. Gratis y open source.',
    'nav.demo': 'Cómo se ve', 'nav.install': 'Instalación', 'nav.security': 'Seguridad', 'nav.label': 'Principal', 'footer.label': 'Enlaces del proyecto',
    'hero.eyebrow': 'Gratis y open source · v{versión}',
    'hero.title': 'Tu celu viejo, ahora una pantalla de escritorio',
    'hero.lede': 'La hora y el clima, tu actividad en GitHub, el uso de Claude y tus fotos, rotando en un Android que tenías en un cajón. Tu Mac junta los datos; sin cuentas ni nube.',
    'hero.cta1': 'Instalala', 'hero.cta2': 'Ver en GitHub',
    'hero.caption': 'La página real de vitrina, con datos de ejemplo. Tocala para pasar de panel.',
    'hero.demoTitle': 'Demo de vitrina, con datos de ejemplo',
    'panels.title': 'Cuatro paneles, uno por vez',
    'panels.sub': 'Rotan solos, cada 15 segundos por defecto. Un panel sin nada para mostrar queda afuera.',
    'panels.alt': '{t}: vista en vivo con datos de ejemplo',
    'panels.clock.t': 'La hora y el clima', 'panels.clock.d': 'El reloj grande, la fecha y el tiempo de tu ciudad. Si se va la Mac, el reloj sigue.',
    'panels.github.t': 'Tu actividad en GitHub', 'panels.github.d': 'Los cuadraditos del último año, tu racha y lo de hoy.',
    'panels.claude.t': 'El uso de Claude', 'panels.claude.d': 'Sesión actual y límite semanal, con marca de ritmo. Opcional, viene apagado.',
    'panels.photos.t': 'Tus fotos', 'panels.photos.d': 'Las de una carpeta de tu Mac. Las verticales se ven enteras.',
    'install.title': 'Instalala en cuatro pasos', 'install.sub': 'Primero, tres cosas que tenés que tener.',
    'needs.mac': 'Una Mac', 'needs.mac.d': 'con Python 3.9 o más nuevo', 'needs.adb': 'adb',
    'needs.phone': 'Un celu Android', 'needs.phone.d': '8 o más nuevo, con depuración USB',
    'step1.t': 'Bajá vitrina y creá el comando', 'step1.d': 'Así podés correr <code>vitrina</code> desde cualquier carpeta. El último comando agrega esa carpeta a tu PATH: abrí una terminal nueva después.',
    'step2.t': 'Completá la configuración',
    'step2.d': 'Corré <code>vitrina</code> una vez: crea <code>config.json</code> y avisa que falta emparejar. Poné tu usuario de GitHub, tu ciudad y la carpeta de fotos.',
    'step3.t': 'Instalá la app en el celu',
    'step3.d': `Bajá el APK del ${link(REPO + '/releases/latest', 'último release')} a tu carpeta Descargas, comprobá su huella SHA-256 con la de las notas y, con el celu enchufado por USB, instalalo.`,
    'step3.c': '# tiene que coincidir con las notas del release',
    'step4.t': 'Emparejá y arrancá',
    'step4.d': 'El celu confirma el emparejado y vitrina se abre sola. La primera vez te guía por los ajustes del celu que hacen falta.',
    'install.note': `Para frenarla: <code>vitrina stop</code>. Nada arranca solo, y si la Mac duerme más de una hora, vitrina se frena. El detalle completo está en el ${link(REPO + '#readme', 'README')}.`,
    'copy': 'Copiar', 'copied': 'Copiado',
    'security.title': 'Cerrada de entrada',
    'security.sub': 'vitrina muestra tus datos en tu escritorio, así que está hecha para que nadie más pueda verlos.',
    'sec1.t': 'Solo el celu emparejado ve algo', 'sec1.d': 'Todo viaja por HTTPS con un certificado hecho en tu Mac, y cada pedido lleva una clave secreta. Sin ella, el server no responde nada útil.',
    'sec2.t': 'Emparejar solo se puede con adb', 'sec2.d': 'Solo adb puede abrir la pantalla de emparejar de la app, así que ninguna otra app del celu puede apuntar vitrina a otro server.',
    'sec3.t': 'No hay cuentas ni nube', 'sec3.d': 'Tus datos no pasan por ningún servidor de vitrina. Al clima se le manda solo el nombre de la ciudad, y el token de Claude solo viaja a Anthropic, nunca al celu.',
    'sec4.t': 'No arranca sola ni toca tus archivos', 'sec4.d': 'Corre solo cuando vos la arrancás. No toca tus archivos ni la configuración de tu Mac: solo guarda lo suyo en su propia carpeta. El código es abierto y el APK está firmado, con su huella en cada release.',
    'closing.title': 'Sacá ese celu del cajón', 'closing.small': 'Gratis, open source, licencia MIT.',
    'footer.credits': `Datos del clima de ${link('https://open-meteo.com/', 'Open-Meteo.com')} (CC BY 4.0). Fuentes Big Shoulders Display y Atkinson Hyperlegible Next (SIL OFL 1.1). Fotos de la demo: dominio público (CC0) de ${link('https://commons.wikimedia.org/', 'Wikimedia Commons')}; autores en ${link(REPO + '/blob/main/website/demo-photos/SOURCES.tsv', 'SOURCES.tsv')}.`,
    'footer.releases': 'Releases', 'footer.readme': 'README', 'footer.license': 'Licencia MIT',
  },
  en: {
    'meta.title': 'vitrina — your old phone, now a desk display',
    'meta.description': 'Turn an old Android phone into a small desk display with the time, weather, your GitHub activity, your Claude usage and your photos. Free and open source.',
    'nav.demo': 'How it looks', 'nav.install': 'Install', 'nav.security': 'Security', 'nav.label': 'Main', 'footer.label': 'Project links',
    'hero.eyebrow': 'Free and open source · v{versión}',
    'hero.title': 'Your old phone, now a desk display',
    'hero.lede': 'The time and weather, your GitHub activity, your Claude usage and your photos, rotating on an Android that was sitting in a drawer. Your Mac gathers the data; no accounts, no cloud.',
    'hero.cta1': 'Install it', 'hero.cta2': 'View on GitHub',
    'hero.caption': 'The real vitrina page, with sample data. Tap it to switch panels.',
    'hero.demoTitle': 'vitrina demo, with sample data',
    'panels.title': 'Four panels, one at a time',
    'panels.sub': 'They rotate on their own, every 15 seconds by default. A panel with nothing to show is left out.',
    'panels.alt': '{t}: live view with sample data',
    'panels.clock.t': 'Time and weather', 'panels.clock.d': "A big clock, the date and your city's weather. If the Mac goes away, the clock keeps going.",
    'panels.github.t': 'Your GitHub activity', 'panels.github.d': "Last year's squares, your streak and today's count.",
    'panels.claude.t': 'Your Claude usage', 'panels.claude.d': 'Current session and weekly limit, with a pace marker. Optional, off by default.',
    'panels.photos.t': 'Your photos', 'panels.photos.d': 'From a folder on your Mac. Portrait photos are shown whole.',
    'install.title': 'Install it in four steps', 'install.sub': 'First, three things you need.',
    'needs.mac': 'A Mac', 'needs.mac.d': 'with Python 3.9 or newer', 'needs.adb': 'adb',
    'needs.phone': 'An Android phone', 'needs.phone.d': '8 or newer, with USB debugging',
    'step1.t': 'Get vitrina and create the command', 'step1.d': 'That lets you run <code>vitrina</code> from any folder. The last command adds that folder to your PATH: open a new terminal afterwards.',
    'step2.t': 'Fill in the config',
    'step2.d': 'Run <code>vitrina</code> once: it creates <code>config.json</code> and tells you pairing is still missing. Add your GitHub username, your city and your photos folder.',
    'step3.t': 'Install the app on the phone',
    'step3.d': `Download the APK from the ${link(REPO + '/releases/latest', 'latest release')} into your Downloads folder, check its SHA-256 against the release notes and, with the phone plugged in over USB, install it.`,
    'step3.c': '# must match the release notes',
    'step4.t': 'Pair and start',
    'step4.d': 'The phone confirms the pairing and vitrina opens by itself. The first time, it walks you through the phone settings it needs.',
    'install.note': `To stop it: <code>vitrina stop</code>. Nothing starts by itself, and if the Mac sleeps for more than an hour, vitrina stops. The full details are in the ${link(REPO + '#readme', 'README')}.`,
    'copy': 'Copy', 'copied': 'Copied',
    'security.title': 'Closed by default',
    'security.sub': 'vitrina shows your data on your desk, so it is built so nobody else can see it.',
    'sec1.t': 'Only the paired phone sees anything', 'sec1.d': 'Everything travels over HTTPS with a certificate made on your Mac, and every request carries a secret key. Without it, the server answers nothing useful.',
    'sec2.t': 'Pairing only works through adb', 'sec2.d': "Only adb can open the app's pairing screen, so no other app on the phone can point vitrina at a different server.",
    'sec3.t': 'No accounts, no cloud', 'sec3.d': "Your data never goes through a vitrina server. The weather service only gets your city's name, and the Claude token only goes to Anthropic, never to the phone.",
    'sec4.t': 'It never starts itself or touches your files', 'sec4.d': "It runs only when you start it. It doesn't touch your files or your Mac's settings: it only keeps its own data in its own folder. The code is open and the APK is signed, with its fingerprint in every release.",
    'closing.title': 'Get that phone out of the drawer', 'closing.small': 'Free, open source, MIT license.',
    'footer.credits': `Weather data from ${link('https://open-meteo.com/', 'Open-Meteo.com')} (CC BY 4.0). Fonts Big Shoulders Display and Atkinson Hyperlegible Next (SIL OFL 1.1). Demo photos: public domain (CC0) from ${link('https://commons.wikimedia.org/', 'Wikimedia Commons')}; authors in ${link(REPO + '/blob/main/website/demo-photos/SOURCES.tsv', 'SOURCES.tsv')}.`,
    'footer.releases': 'Releases', 'footer.readme': 'README', 'footer.license': 'MIT license',
  },
};

const READY_FALLBACK_MS = 4000;
let current = 'es';
const fallbackTimers = new WeakMap();

function pickLang() {
  const asked = new URLSearchParams(location.search).get('lang');
  if (asked === 'es' || asked === 'en') return asked;
  try {
    const saved = localStorage.getItem('lang');
    if (saved === 'es' || saved === 'en') return saved;
  } catch (e) { /* storage can be unavailable (private window) */ }
  return (navigator.language || '').slice(0, 2) === 'es' ? 'es' : 'en';
}

// A demo shows up once it says it is ready, or READY_FALLBACK_MS after it loaded, whichever comes first.
function armFallback(iframe) {
  clearTimeout(fallbackTimers.get(iframe));
  fallbackTimers.set(iframe, setTimeout(() => iframe.classList.add('ready'), READY_FALLBACK_MS));
}

function applyLang(lang) {
  current = lang;
  const s = STRINGS[lang];
  const fill = (text) => text.replace('{versión}', document.documentElement.dataset.version);
  document.documentElement.lang = lang;
  document.title = s['meta.title'];
  for (const sel of ['meta[name="description"]', 'meta[property="og:description"]']) {
    document.querySelector(sel).setAttribute('content', s['meta.description']);
  }
  document.querySelector('meta[property="og:title"]').setAttribute('content', s['meta.title']);
  for (const el of document.querySelectorAll('[data-i]')) {
    if (s[el.dataset.i] !== undefined) el.innerHTML = fill(s[el.dataset.i]);
  }
  for (const el of document.querySelectorAll('[data-i-attr]')) {
    const [attr, key] = el.dataset.iAttr.split(':');
    el.setAttribute(attr, s[key]);
  }
  for (const item of document.querySelectorAll('[data-panel]')) {
    const label = s['panels.alt'].replace('{t}', s[`panels.${item.dataset.panel}.t`]);
    item.querySelector('.screen').setAttribute('aria-label', label);
  }
  for (const span of document.querySelectorAll('#lang span')) {
    if (span.lang === lang) span.setAttribute('aria-current', 'true');
    else span.removeAttribute('aria-current');
  }
  try { localStorage.setItem('lang', lang); } catch (e) { /* see pickLang */ }
  for (const iframe of document.querySelectorAll('iframe[data-src]')) {
    const url = new URL(iframe.dataset.src, location.href);
    url.searchParams.set('lang', lang);
    clearTimeout(fallbackTimers.get(iframe)); // a slow old load must not reveal the new one early
    iframe.classList.remove('ready');
    iframe.src = url.href;
  }
}

function setupCopy() {
  const buttons = document.querySelectorAll('.copy-btn');
  if (!navigator.clipboard) {
    for (const b of buttons) b.hidden = true;
    return;
  }
  for (const b of buttons) {
    b.addEventListener('click', async () => {
      const pre = b.parentElement.querySelector('pre').cloneNode(true);
      for (const c of pre.querySelectorAll('.c')) c.remove();
      try {
        await navigator.clipboard.writeText(pre.textContent.replace(/[ \t]+$/gm, '').trim());
      } catch (e) { return; }
      b.textContent = STRINGS[current].copied;
      setTimeout(() => { b.textContent = STRINGS[current].copy; }, 1500);
    });
  }
}

// --s drives the phone frame and the screen together, so it lives on their common box.
function fitScreens() {
  for (const screen of document.querySelectorAll('.screen')) {
    const box = screen.closest('[data-box]');
    const style = getComputedStyle(box);
    const room = box.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    const s = Math.min(Number(screen.dataset.max), room / Number(screen.dataset.frame));
    box.style.setProperty('--s', s);
  }
}

function setupReady() {
  const iframes = [...document.querySelectorAll('iframe[data-src]')];
  for (const iframe of iframes) iframe.addEventListener('load', () => armFallback(iframe));
  window.addEventListener('message', (event) => {
    if (event.origin !== location.origin || !event.data || event.data.vitrinaDemo !== 'ready') return;
    for (const iframe of iframes) {
      if (iframe.contentWindow === event.source) iframe.classList.add('ready');
    }
  });
}

setupReady();
setupCopy();
fitScreens();
if (window.ResizeObserver) {
  const observer = new ResizeObserver(fitScreens);
  for (const box of document.querySelectorAll('[data-box]')) observer.observe(box);
}
window.addEventListener('resize', fitScreens);
document.getElementById('lang').addEventListener('click', () => applyLang(current === 'es' ? 'en' : 'es'));
applyLang(pickLang());
