// OXXai çevrimdışı önbellek: uygulama dosyaları önbellekten, sayfa ve veriler önce ağdan
const C = "oxxai-v151";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/oxxai2-192.png", "icons/oxxai2-512.png", "icons/oxxai-mark.webp", "icons/oxxai-word.webp", "icons/oxxai-mark-crown-s.webp", "icons/oxxai-logo.webp", "icons/oxxai-splash.webp", "icons/oxxai-at.webp",
  // uygulama paketleri (index.html sırasıyla; ?v= içerik özeti, lab/yayin_listesi.py kur/damga günceller)
  "js/baslangic.js?v=7f0bf10950", "js/core.js?v=4c38457194", "js/bot.js?v=a83e9e8f1b", "js/ekran.js?v=e1865ef08a", "js/at.js?v=354cb8bbd9", "js/futbol.js?v=2ceb4bda4c", "css/govde.css?v=e23efdc0e2", "css/govde-2.css?v=346287e181", "js/kupo.js?v=06fcfa8886", "js/at-kupo.js?v=05d843f9e7", "js/pazar.js?v=d37df0f43a", "js/at2.js?v=e8391b65d7", "js/canli-gt.js?v=fe3aed81e4", "js/at5.js?v=f43230d92c", "js/arayuz.js?v=b9ef4cd29f", "js/ses.js?v=17b691924d", "js/paylas.js?v=c9e0debe8f", "js/guvenilirlik.js?v=d0b55a7c7e", "js/canli-isaret.js?v=f07ded97da", "css/katmanlar.css?v=c584ef9caa", "js/katmanlar.js?v=d665b03b80"];
self.addEventListener("install", e => { e.waitUntil(caches.open(C).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => (k.startsWith("oxxai-") || k.startsWith("bulutoxx-")) && k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  // Canlı uç noktalar (iddaa, ESPN) başka kökendedir: hiç dokunulmaz → her zaman doğrudan ağdan (önbelleğe alınmaz, skor donmaz)
  if (e.request.method !== "GET" || u.origin !== location.origin) return;
  const fresh = u.pathname.includes("/data/") || u.pathname.endsWith("/") || u.pathname.endsWith("index.html");
  if (fresh) {
    const key = u.origin + u.pathname;   // ?t=… sorguları aynı kayda yazılır: önbellek büyümez, çevrimdışı en yeni veri döner
    e.respondWith(fetch(e.request, {cache: "no-store"}).then(r => { if (r.ok) { const c = r.clone(); caches.open(C).then(x => x.put(key, c)); } return r; })
      .catch(() => caches.match(key)));
  } else if (/\/(js|css)\/[^/]+\.(js|css)$/.test(u.pathname)) {
    // Paketler (js/, css/): adres ?v=<içerik özeti> taşır → aynı adres hep aynı içerik: önce önbellek, yoksa ağ.
    // Yeni sürümün index.html'i (her zaman ağdan) yeni ?v= ister → eski JS önbellekten gelmez. Aynı dosyanın eski sürümleri silinir.
    e.respondWith(caches.match(e.request).then(m => m || fetch(e.request).then(r => {
      if (r.ok) { const c = r.clone(); caches.open(C).then(x => x.keys().then(ks => Promise.all(ks.filter(k => { const q = new URL(k.url); return q.pathname === u.pathname && q.search !== u.search; }).map(k => x.delete(k)))).then(() => x.put(e.request, c))); }
      return r; })));
  } else {
    e.respondWith(caches.match(e.request).then(m => m || fetch(e.request).then(r => { const c = r.clone(); caches.open(C).then(x => x.put(e.request, c)); return r; })));
  }
});
// Gol bildirimine dokununca uygulamayı aç
self.addEventListener("notificationclick", e => {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({type: "window"}).then(ws => ws.length ? ws[0].focus() : self.clients.openWindow("./#canli")));
});
