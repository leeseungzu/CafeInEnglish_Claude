// 카영 실시간 "같이 있기" 서버 (Cloudflare Workers + Durable Objects)
// - 자유 입력 없음: 이름·퀵챗·리액션은 모두 번호로만 주고받는다.
// - 한 방 최대 20명, 꽉 차면 다음 호점으로 자동 배정.
import { DurableObject } from "cloudflare:workers";

const ROOM_MAX = 20;
const ORIGINS = [/^https:\/\/(www\.)?cafeinenglish\.com$/, /^http:\/\/localhost(:\d+)?$/, /^http:\/\/127\.0\.0\.1(:\d+)?$/];
const N_ADJ = 40, N_DRINK = 12, N_QC = 60, N_EMO = 6; // 클라이언트 목록 길이 상한
const okOrigin = (o) => !o || ORIGINS.some((r) => r.test(o));
const json = (d, s = 200) => new Response(JSON.stringify(d), { status: s, headers: { "content-type": "application/json", "access-control-allow-origin": "*", "cache-control": "no-store" } });
const int = (v, max) => Number.isInteger(v) && v >= 0 && v < max;
const num = (v, lim) => typeof v === "number" && isFinite(v) && Math.abs(v) <= lim;

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!okOrigin(req.headers.get("origin"))) return new Response("forbidden", { status: 403 });
    const lobby = env.LOBBY.get(env.LOBBY.idFromName("main"));
    if (url.pathname === "/stats") return lobby.fetch("https://lobby/stats");
    if (url.pathname === "/feedback") return feedback(req, env);
    if (url.pathname === "/ws") {
      if (req.headers.get("upgrade") !== "websocket") return new Response("expected websocket", { status: 426 });
      const room = await (await lobby.fetch("https://lobby/assign")).text();
      const stub = env.ROOM.get(env.ROOM.idFromName("room-" + room));
      const u = new URL(req.url); u.searchParams.set("room", room);
      return stub.fetch(new Request(u, req));
    }
    return new Response("kayoung realtime ok");
  },
};

// 의견 보내기: 카페 → 이 서버 → 승주님 Google Apps Script(MailApp) → Gmail
// FEEDBACK_URL, FEEDBACK_TOKEN 은 Cloudflare 대시보드의 비밀 변수(Secrets)에 둬요(저장소에 안 올라감).
const KINDS = ["좋았던 점", "불편한 점", "오류 신고", "아이디어"];
const fbSeen = new Map();
async function feedback(req, env) {
  const cors = { "access-control-allow-origin": req.headers.get("origin") || "*", "access-control-allow-methods": "POST, OPTIONS", "access-control-allow-headers": "content-type" };
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  if (req.method !== "POST") return new Response("method", { status: 405, headers: cors });
  const ip = req.headers.get("cf-connecting-ip") || "?"; const now = Date.now();
  const last = fbSeen.get(ip) || 0; if (now - last < 20000) return new Response(JSON.stringify({ ok: false, why: "wait" }), { status: 429, headers: cors });
  let d; try { d = await req.json(); } catch (e) { return new Response("bad", { status: 400, headers: cors }); }
  const text = String(d.text || "").trim().slice(0, 1000); const kind = KINDS.includes(d.kind) ? d.kind : "의견";
  if (!text) return new Response(JSON.stringify({ ok: false, why: "empty" }), { status: 400, headers: cors });
  fbSeen.set(ip, now); if (fbSeen.size > 500) fbSeen.clear();
  if (!env.FEEDBACK_URL) return new Response(JSON.stringify({ ok: false, why: "setup" }), { status: 503, headers: cors });
  const info = [String(d.dev || "").slice(0, 10), String(d.name || "").slice(0, 30), String(d.ua || "").slice(0, 160), new Date(now + 9 * 3600e3).toISOString().slice(0, 16).replace("T", " ") + " KST"].join(" · ");
  const r = await fetch(env.FEEDBACK_URL, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ token: env.FEEDBACK_TOKEN || "", kind, text, info }), redirect: "manual" });
  const ok = r.status < 400;
  return new Response(JSON.stringify({ ok }), { status: ok ? 200 : 502, headers: { ...cors, "content-type": "application/json" } });
}

// 방별 인원 집계 + 배정
export class Lobby extends DurableObject {
  constructor(ctx, env) { super(ctx, env); this.counts = null; }
  async load() { if (!this.counts) this.counts = (await this.ctx.storage.get("counts")) || {}; }
  async fetch(req) {
    await this.load();
    const p = new URL(req.url).pathname;
    if (p === "/assign") {
      let n = 1; while ((this.counts[n] || 0) >= ROOM_MAX) n++;
      this.counts[n] = (this.counts[n] || 0) + 1; // 입장 예약, 방에서 정확한 수로 다시 보고
      await this.ctx.storage.put("counts", this.counts);
      return new Response(String(n));
    }
    if (p === "/report") {
      const { room, count } = await req.json();
      if (count > 0) this.counts[room] = count; else delete this.counts[room];
      await this.ctx.storage.put("counts", this.counts);
      return new Response("ok");
    }
    if (p === "/stats") {
      const total = Object.values(this.counts).reduce((a, b) => a + b, 0);
      return json({ total, rooms: Object.keys(this.counts).length });
    }
    return new Response("nf", { status: 404 });
  }
}

// 한 호점(방)
export class Room extends DurableObject {
  constructor(ctx, env) { super(ctx, env); ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair("ping", "pong")); }
  alive(w, now) { // 마지막 신호가 60초 안에 있었던 연결만 살아 있는 사람으로 본다
    const a = w.deserializeAttachment() || {}; const ts = Math.max(a.t || 0, a.c || 0, (this.ctx.getWebSocketAutoResponseTimestamp(w) || new Date(0)).getTime());
    return now - ts < 60000;
  }
  live(gone) { const now = Date.now(); return this.ctx.getWebSockets().filter((w) => w !== gone && this.alive(w, now)); }
  async alarm() { // 30초마다 끊긴 연결 정리
    const now = Date.now(); let changed = false;
    for (const w of this.ctx.getWebSockets()) if (!this.alive(w, now)) { const a = w.deserializeAttachment(); try { w.close(1001, "stale"); } catch (e) {} if (a && a.p) this.bcast({ t: "leave", id: a.id }, w); changed = true; }
    if (changed) await this.report();
    if (this.ctx.getWebSockets().length) await this.ctx.storage.setAlarm(Date.now() + 30000);
  }
  async fetch(req) {
    const room = Number(new URL(req.url).searchParams.get("room")) || 1;
    await this.ctx.storage.put("room", room);
    const [client, server] = Object.values(new WebSocketPair());
    const id = crypto.randomUUID().slice(0, 8);
    this.ctx.acceptWebSocket(server); // 하이버네이션: 조용할 땐 비용 없음
    server.serializeAttachment({ id, p: null, t: 0, n: 0, c: Date.now() });
    server.send(JSON.stringify({ t: "welcome", id, room, others: this.peers(server) }));
    await this.report();
    if (!(await this.ctx.storage.getAlarm())) await this.ctx.storage.setAlarm(Date.now() + 30000);
    return new Response(null, { status: 101, webSocket: client });
  }
  peers(except) {
    return this.live(except).map((w) => w.deserializeAttachment()).filter((a) => a && a.p).map((a) => ({ id: a.id, ...a.p }));
  }
  bcast(msg, except) { const s = JSON.stringify(msg); for (const w of this.ctx.getWebSockets()) if (w !== except) { try { w.send(s); } catch (e) {} } }
  async report(gone) {
    const room = (await this.ctx.storage.get("room")) || 1;
    const count = this.live(gone).filter((w) => (w.deserializeAttachment() || {}).p).length;
    await this.env.LOBBY.get(this.env.LOBBY.idFromName("main")).fetch("https://lobby/report", { method: "POST", body: JSON.stringify({ room, count }) });
    this.bcast({ t: "count", room, count });
  }
  async webSocketMessage(ws, raw) {
    if (typeof raw !== "string" || raw.length > 300) return;
    const a = ws.deserializeAttachment(); const now = Date.now();
    if (now - a.t > 1000) { a.t = now; a.n = 0; } if (++a.n > 6) { ws.serializeAttachment(a); return; } // 초당 6개 제한
    let m; try { m = JSON.parse(raw); } catch (e) { return; }
    if (m.t === "hello" && int(m.adj, N_ADJ) && int(m.drink, N_DRINK)) {
      const first = !a.p;
      a.p = { adj: m.adj, drink: m.drink, x: 0, z: 0, seat: null };
      ws.serializeAttachment(a);
      this.bcast({ t: first ? "join" : "upd", id: a.id, ...a.p }, ws);
      if (first) await this.report();
    } else if (!a.p) { ws.serializeAttachment(a); return; }
    else if (m.t === "pos" && num(m.x, 3000) && num(m.z, 3000)) {
      a.p.x = Math.round(m.x); a.p.z = Math.round(m.z);
      a.p.seat = typeof m.seat === "string" && /^[a-z0-9]{1,6}:\d{1,2}$/.test(m.seat) ? m.seat : null;
      ws.serializeAttachment(a);
      this.bcast({ t: "pos", id: a.id, x: a.p.x, z: a.p.z, seat: a.p.seat }, ws);
    } else if (m.t === "qc" && int(m.i, N_QC)) { ws.serializeAttachment(a); this.bcast({ t: "qc", id: a.id, i: m.i }, ws); }
    else if (m.t === "emo" && int(m.i, N_EMO)) { ws.serializeAttachment(a); this.bcast({ t: "emo", id: a.id, i: m.i }, ws); }
    else ws.serializeAttachment(a);
  }
  async webSocketClose(ws) { const a = ws.deserializeAttachment(); try { ws.close(); } catch (e) {} if (a && a.p) this.bcast({ t: "leave", id: a.id }, ws); await this.report(ws); }
  async webSocketError(ws) { await this.webSocketClose(ws); }
}
