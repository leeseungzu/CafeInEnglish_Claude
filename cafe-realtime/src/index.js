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
  async fetch(req) {
    const room = Number(new URL(req.url).searchParams.get("room")) || 1;
    await this.ctx.storage.put("room", room);
    const [client, server] = Object.values(new WebSocketPair());
    const id = crypto.randomUUID().slice(0, 8);
    this.ctx.acceptWebSocket(server); // 하이버네이션: 조용할 땐 비용 없음
    server.serializeAttachment({ id, p: null, t: 0, n: 0 });
    server.send(JSON.stringify({ t: "welcome", id, room, others: this.peers(server) }));
    await this.report();
    return new Response(null, { status: 101, webSocket: client });
  }
  peers(except) {
    return this.ctx.getWebSockets().filter((w) => w !== except).map((w) => w.deserializeAttachment()).filter((a) => a && a.p).map((a) => ({ id: a.id, ...a.p }));
  }
  bcast(msg, except) { const s = JSON.stringify(msg); for (const w of this.ctx.getWebSockets()) if (w !== except) { try { w.send(s); } catch (e) {} } }
  async report() {
    const room = (await this.ctx.storage.get("room")) || 1;
    const count = this.ctx.getWebSockets().length;
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
  async webSocketClose(ws) { const a = ws.deserializeAttachment(); try { ws.close(); } catch (e) {} if (a && a.p) this.bcast({ t: "leave", id: a.id }, ws); await this.report(); }
  async webSocketError(ws) { await this.webSocketClose(ws); }
}
