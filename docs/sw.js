// 카페인영어 홈 화면 앱: 페이지는 항상 서버에 새로 확인(브라우저 10분 캐시도 건너뜀), 끊기면 저장본. 글꼴·음성·이미지는 저장해 빠르게
const C = "ky-v2";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;
  if (u.pathname.startsWith("/assets/") || u.pathname.startsWith("/audio/")) {
    e.respondWith(caches.open(C).then(c => c.match(e.request).then(r => r || fetch(e.request).then(n => { if (n.ok) c.put(e.request, n.clone()); return n; }))));
  } else if (e.request.mode === "navigate") {
    // 2026-11-20: 30분 안에 받아 둔 페이지는 바로 보여 주고(탭 이동이 즉시), 뒤에서 새로 받아 다음 방문에 반영. 오래된 저장본이면 서버 먼저
    const net = fetch(u.href, { cache: "no-cache", credentials: "same-origin" }).then(n => {
      if (n.redirected) return Response.redirect(n.url, 302);
      if (n.ok) { const cp = n.clone(); caches.open(C).then(c => c.put(e.request.url, cp)); } return n;
    });
    e.respondWith(caches.match(e.request.url).then(hit => {
      const age = hit ? Date.now() - Date.parse(hit.headers.get("date") || 0) : Infinity;
      if (hit && age < 30 * 60 * 1000) { e.waitUntil(net.catch(() => {})); return hit; }
      return net.catch(() => hit || caches.match(e.request.url));
    }));
  }
});
// 탭·칸 페이지 미리 받기 (페이지가 보내 주는 주소만, 같은 사이트만)
self.addEventListener("message", e => {
  const urls = (e.data && e.data.prefetch) || [];
  e.waitUntil(caches.open(C).then(c => Promise.all(urls.slice(0, 12).map(h => {
    const url = new URL(h, location.origin); if (url.origin !== location.origin) return;
    return c.match(url.href).then(hit => {
      if (hit && Date.now() - Date.parse(hit.headers.get("date") || 0) < 10 * 60 * 1000) return;
      return fetch(url.href, { cache: "no-cache", credentials: "same-origin" }).then(n => { if (n.ok && !n.redirected) return c.put(url.href, n); }).catch(() => {});
    });
  }))));
});
