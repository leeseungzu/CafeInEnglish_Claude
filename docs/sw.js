// 카페인영어 홈 화면 앱: 페이지는 항상 새로 받고(없으면 저장본), 글꼴·음성·이미지는 저장해 빠르게
const C = "ky-v1";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;
  if (u.pathname.startsWith("/assets/") || u.pathname.startsWith("/audio/")) {
    e.respondWith(caches.open(C).then(c => c.match(e.request).then(r => r || fetch(e.request).then(n => { if (n.ok) c.put(e.request, n.clone()); return n; }))));
  } else if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).then(n => { const cp = n.clone(); caches.open(C).then(c => c.put(e.request, cp)); return n; }).catch(() => caches.match(e.request)));
  }
});
