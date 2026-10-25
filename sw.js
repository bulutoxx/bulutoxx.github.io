// BULUTOXX çevrimdışı önbellek: uygulama dosyaları önbellekten, sayfa ve veriler önce ağdan
const C = "bulutoxx-v75";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/mark.png", "icons/logo-full.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(C).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith("bulutoxx-") && k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;
  const fresh = u.pathname.includes("/data/") || u.pathname.endsWith("/") || u.pathname.endsWith("index.html");
  if (fresh) {
    const key = u.origin + u.pathname;   // ?t=… sorguları aynı kayda yazılır: önbellek büyümez, çevrimdışı en yeni veri döner
    e.respondWith(fetch(e.request, {cache: "no-store"}).then(r => { if (r.ok) { const c = r.clone(); caches.open(C).then(x => x.put(key, c)); } return r; })
      .catch(() => caches.match(key)));
  } else {
    e.respondWith(caches.match(e.request).then(m => m || fetch(e.request).then(r => { const c = r.clone(); caches.open(C).then(x => x.put(e.request, c)); return r; })));
  }
});
// Gol bildirimine dokununca uygulamayı aç
self.addEventListener("notificationclick", e => {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({type: "window"}).then(ws => ws.length ? ws[0].focus() : self.clients.openWindow("./#canli")));
});
