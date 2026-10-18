/* 카페인영어 · 내 공부방 '오늘의 한 잔 5분 루틴' (가입 없이, 기록은 이 기기에만) */
(function () {
  const root = document.getElementById("today-app");
  if (!root) return;
  const logRoot = document.getElementById("log-app");
  // ── 탭: 오늘 · 오답노트 · 필사 노트 · 기록 (주소 #wrong 등으로 바로 열려요) ──
  const TAB_OF = { routine: "today", review: "today", today: "today", wrong: "wrong", copy: "copy", log: "log", backup: "log" };
  function tabCounts() {
    const n = k => { try { return Object.keys(JSON.parse(localStorage.getItem(k)) || {}).length; } catch (e) { return 0; } };
    const w = n("cafein_wrong_v1");
    // 오답노트만 '다시 볼 것'이 있다는 배지로 (필사 노트는 모아 두는 곳이라 숫자 없음)
    document.querySelectorAll(".js-tn-w").forEach(x => { x.textContent = w > 99 ? "99+" : w || ""; x.hidden = !w; x.setAttribute("aria-label", w ? `다시 볼 문제 ${w}개` : ""); });
  }
  function showTab(t, push) {
    document.querySelectorAll(".nbt [data-tab]").forEach(b => { const on = b.dataset.tab === t; b.classList.toggle("on", on); b.setAttribute("aria-selected", String(on)); });
    document.querySelectorAll(".nbp").forEach(p => p.hidden = p.dataset.p !== t);
    if (push) history.replaceState(null, "", location.pathname + location.search + (t === "today" ? "" : "#" + t));
    tabCounts();
  }
  document.querySelector(".nbt")?.addEventListener("click", ev => {
    const b = ev.target.closest("[data-tab]"); if (!b) return;
    showTab(b.dataset.tab, true);
    const band = document.querySelector(".nb-band"); if (band && band.getBoundingClientRect().top < 0) band.scrollIntoView({ block: "start" });
    ga("notes_tab", { tab: b.dataset.tab });
  });
  document.querySelector(".nb-band")?.addEventListener("click", () => setTimeout(tabCounts, 300));
  addEventListener("hashchange", () => { const t = TAB_OF[location.hash.slice(1)]; if (t) showTab(t); });
  const D = JSON.parse(document.getElementById("page-data").textContent || "{}");
  const DAILY = D.daily || [], POOL = D.pool || {}, SRCS = D.goals || [], CUP = D.cup || "";
  const KEY = "ky_today_v1";
  let S;
  try { S = JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { S = {}; }
  S.days = S.days || {}; S.learned = S.learned || []; S.ptr = S.ptr || {}; S.src = S.src || "daily";
  const ga = (n, o) => { try { window.gtag && gtag("event", n, o || {}); } catch (e) {} };
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // 날짜는 한국 시간 기준 (홈 '오늘의 한 잔'과 같은 날 바뀜)
  const DAY = Math.floor((Date.now() / 1000 + 9 * 3600) / 86400);
  const ymd = n => new Date(n * 864e5).toISOString().slice(0, 10);
  const TODAY = ymd(DAY);
  const ago = s => Math.round((new Date(TODAY) - new Date(s)) / 864e5);
  const done0 = r => !!(r && r.l && r.s && r.r);
  S.stamps = S.stamps || []; S.runs = S.runs || {};
  Object.keys(S.days).forEach(k => { if (done0(S.days[k]) && S.stamps.indexOf(k) < 0) S.stamps.push(k); });
  Object.keys(S.runs).forEach(k => { if (k.slice(0, 10) !== new Date(Math.floor((Date.now() / 1000 + 9 * 3600) / 86400) * 864e5).toISOString().slice(0, 10)) delete S.runs[k]; });
  // 날짜 문자열(s)이면 그날 도장이 있는지, 기록(r)이면 세 단계를 다 했는지
  const done = x => typeof x === "string" ? S.stamps.indexOf(x) > -1 : done0(x);
  const SRC_NAME = { daily: "오늘의 한 잔" };
  SRCS.forEach(g => SRC_NAME[g.id] = g.name);
  let open = null;
  // 홈에서 목표를 고르고 들어온 경우 (?goal=travel)
  const gq = new URLSearchParams(location.search).get("goal");
  if (gq && (gq === "daily" || POOL[gq])) { S.src = gq; save(); history.replaceState(null, "", location.pathname + "#routine"); }

  function pickItem(src) {
    if (src === "daily" || !POOL[src] || !POOL[src].length) return DAILY.length ? DAILY[DAY % DAILY.length] : null;
    const p = POOL[src], i = (S.ptr[src] || 0) % p.length;
    S.ptr[src] = (i + 1) % p.length;
    return p[i];
  }
  function today() {
    let r = S.days[TODAY];
    if (r && r.src !== S.src) { S.runs[TODAY + "|" + r.src] = r; const back = S.runs[TODAY + "|" + S.src]; if (back) { r = S.days[TODAY] = back; return r; } }
    if (!r || r.src !== S.src) {
      const it = pickItem(S.src);
      if (!it) return null;
      r = S.days[TODAY] = { src: S.src, en: it.en, ko: it.ko, a: it.a, p: it.p, l: 0, s: 0, r: 0 };
      const old = S.learned.filter(x => x.d !== TODAY);
      srsSync();
      const dv = dueList().find(v => v.en !== it.en);
      const pk = (dv && old.find(x => x.en === dv.en)) || old.find(x => ago(x.d) === 3) || old.find(x => ago(x.d) === 7) || old[Math.floor(Math.random() * old.length)];
      const q = pk ? { en: pk.en, ko: pk.ko, a: pk.a, ago: ago(pk.d) } : { en: it.en, ko: it.ko, a: it.a, ago: 0 };
      const bank = [...new Set([...DAILY, ...Object.values(POOL).flat()].map(x => x.en))].filter(e => e !== q.en);
      const o = [q.en];
      while (o.length < 4 && bank.length) o.push(bank.splice(Math.floor(Math.random() * bank.length), 1)[0]);
      q.o = o.sort(() => Math.random() - .5);
      r.q = q; save();
    }
    return r;
  }
  // ── 간격 반복: 말해 본 문장을 1·3·7·14·30·60일 뒤에 다시 꺼내요 ──
  const IV = [1, 3, 7, 14, 30, 60];
  const dnum = d => Math.round(Date.parse(d) / 864e5);
  function srsSync() {
    S.srs = S.srs || {};
    S.learned.forEach(x => { if (x.en && !S.srs[x.en]) S.srs[x.en] = { st: 0, due: dnum(x.d) + IV[0], en: x.en, ko: x.ko, a: x.a, p: x.p || "", from: SRC_NAME[x.src] || "오늘의 한 잔", at: dnum(x.d) }; });
  }
  const dueList = () => Object.values(S.srs || {}).filter(v => v.due <= DAY).sort((a, b) => a.due - b.due || a.st - b.st);
  // 발음 듣기 버튼은 어디서나 같은 동그란 스피커 아이콘 (글자 버튼은 줄바꿈되며 균형이 깨져요)
  const SPK = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/></svg>';
  let rvShow = false, saidAll = false;
  // 이 문장이 어디서 왔는지: 'I'm down 글에서 · 2일 전에 담았어요'
  function rvSrc(v) {
    const from = v.t ? `${esc(v.t)} 글에서` : v.from ? `${esc(v.from)}에서` : "";
    const d = typeof v.at === "number" ? DAY - v.at : -1;
    const when = d < 0 ? "" : d === 0 ? "오늘 담았어요" : `${d}일 전에 담았어요`;
    if (!from && !when) return "";
    return `<p class="rv-src">${v.t && v.p ? `<a href="${esc(v.p)}">${from}</a>` : from}${from && when ? " · " : ""}${when}</p>`;
  }
  function rvBlock() {
    const all = Object.values(S.srs || {}); if (!all.length) return "";
    const due = dueList(), v = due[0];
    if (!v) {
      const nx = all.reduce((m, x) => Math.min(m, x.due), 1e9), nn = all.filter(x => x.due === nx).length;
      return `<section class="rv" id="review"><div class="rv-top"><b>오늘의 복습</b><span class="rv-n done">${all.length}개 담김</span></div><p class="rv-empty">지금 꺼낼 문장은 없어요. ${nx - DAY <= 1 ? "내일" : (nx - DAY) + "일 뒤"} ${nn}개가 찾아와요.</p><p class="rv-tip">잊을 즈음 다시 보면 오래 남아요 · 1 → 3 → 7 → 14 → 30일 뒤</p></section>`;
    }
    const stg = ["첫", "두 번째", "세 번째", "네 번째", "다섯 번째", "여섯 번째"][v.st] || "다시";
    return `<section class="rv" id="review"><div class="rv-top"><b>오늘의 복습</b><span class="rv-n">${due.length}개 남음</span></div>
<p class="rv-k">${stg} 복습 · 한국어만 보고 영어로 말해 보세요</p><p class="rv-q">“${esc(v.ko)}”</p>${rvSrc(v)}
${rvShow ? `<div class="rv-a"><b>${esc(v.en)}</b>${v.a ? `<button type="button" class="rt-spk" data-play="${v.a}" aria-label="원어민 발음 듣기">${SPK}</button>` : ""}</div>
<div class="rv-btns"><button type="button" class="rv-b" data-rv="again">헷갈려요<small>내일 다시</small></button><button type="button" class="rv-b ok" data-rv="ok">기억났어요<small>${IV[Math.min(v.st + 1, IV.length - 1)]}일 뒤에</small></button></div>`
      : `<button type="button" class="rv-show" data-rv="show">정답 보기</button>`}
<p class="rv-tip">잊을 즈음 다시 보면 오래 남아요 · 1 → 3 → 7 → 14 → 30일 뒤</p></section>`;
  }
  function learn(r) {
    if (r.l && r.s && !S.learned.some(x => x.d === TODAY && x.en === r.en)) { S.learned.push({ en: r.en, ko: r.ko, a: r.a, d: TODAY, src: r.src }); }
  }
  function streak() {
    let n = 0, d = DAY - (done(TODAY) ? 0 : 1);
    while (done(ymd(d))) { n++; d--; }
    return n;
  }
  let cur = null;
  function play(src, rate, times, onEnd) {
    if (cur) cur.pause();
    let n = 0; const a = new Audio(src); a.playbackRate = rate || 1; cur = a;
    a.onended = () => { n++; if (n < (times || 1) && cur === a) setTimeout(() => { a.currentTime = 0; a.play(); }, 600); else if (onEnd) onEnd(); };
    a.play().catch(() => onEnd && onEnd());
  }
  const IC = {
    l: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1v-6h3zM3 19a2 2 0 0 0 2 2h1v-6H3z"/></svg>',
    s: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>',
    r: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/></svg>'
  };
  function row(k, t, sub, r) {
    const ok = r[k], isOpen = open === k;
    return `<div class="rt-step${isOpen ? " open" : ""}"><button type="button" class="act rt-act${ok ? " rt-done" : ""}${isOpen ? " rt-open" : ""}" data-step="${k}"><span class="act-ic">${IC[k]}</span><span class="act-t"><b>${t}</b><small>${sub}</small></span><span class="act-r">${ok ? '<span class="rt-ok">✓</span>' : '<i class="chev">›</i>'}</span></button>${isOpen ? '<div class="rt-panel">' + panel(k, r) + "</div>" : ""}</div>`;
  }
  function panel(k, r) {
    if (k === "l") return `<div class="rt-3"><button class="rt-pl d" data-act="listen">▶ 3번 듣기</button><button class="rt-pl" data-act="slow">천천히 듣기</button><a class="rt-pl" href="${r.p}">자세히 배우기</a></div>`;
    if (k === "s") {
      const box = window.KY_SAY ? KY_SAY.box(r.en) : '<div class="ks"><div class="ks-row"><span class="ks-t"><b>소리 내어 3번 말해 보세요</b><small>다 말했으면 오른쪽 버튼을 눌러요</small></span><button type="button" class="ks-done">다 말했어요</button></div></div>';
      return `<p class="rt-q">“${esc(r.ko)}”</p><p class="rt-sub">한국어만 보고 영어로 말해 보세요.</p>${box}<div class="rt-reveal" id="rt-reveal" hidden></div><button type="button" class="rt-link" data-act="reveal">정답 먼저 보기</button>`;
    }
    const q = r.q;
    return `<p class="rt-q">“${esc(q.ko)}”를 영어로?</p><div class="rt-qz">${q.o.map(en => `<button data-q="${esc(en)}"${r.r && en === q.en ? ' class="right"' : ""}>${esc(en)}</button>`).join("")}</div>`;
  }
  function render() {
    srsSync();
    const r = today();
    if (!r) { root.innerHTML = ""; return; }
    if (open === null) open = !r.l ? "l" : !r.s ? "s" : !r.r ? "r" : "";
    const n = r.l + r.s + r.r, w = r.en.split(" "), last = w.pop();
    // 이번 주 (월~일)
    const mon = DAY - ((new Date(TODAY).getUTCDay() + 6) % 7);
    let wk = "", cnt = 0;
    for (let k = 0; k < 7; k++) {
      const s = ymd(mon + k), ok = done(s); if (ok) cnt++;
      wk += `<div class="rt-dy${ok ? " on" : ""}${s === TODAY ? " td" : ""}"><i>${ok ? `<svg viewBox="0 0 24 24" width="18" height="18" aria-label="완료"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/></svg>` : ""}</i>${s === TODAY ? "오늘" : "월화수목금토일"[k]}</div>`;
    }
    const said = []; { const sn = new Set(); S.learned.slice().reverse().forEach(x => { if (x.en && !sn.has(x.en)) { sn.add(x.en); said.push(x); } }); }
    const st = streak();
    const set = new Set((r.src === "daily" ? DAILY : POOL[r.src] || []).map(x => x.en));
    const got = new Set(S.learned.filter(x => set.has(x.en)).map(x => x.en)).size, pct = set.size ? Math.round(got / set.size * 100) : 0;
    S.prog = { src: r.src, name: SRC_NAME[r.src] || "오늘의 한 잔", n: got, t: set.size, streak: st, day: TODAY, done: n === 3 };
    if (n === 3 && S.stamps.indexOf(TODAY) < 0) S.stamps.push(TODAY);
    if (n === 3 && !r.ga) { r.ga = 1; ga("routine_done", { goal: r.src }); }
    const stamped = done(TODAY);
    // 이번 주 목표 3잔: 처음 채운 날 한 번 축하
    const GOAL = 3, met = cnt >= GOAL, cel = met && S.wkCel !== mon;
    if (cel) { S.wkCel = mon; ga("week_goal", { cups: cnt }); }
    save();
    const due = dueList(), srsN = Object.keys(S.srs || {}).length;
    const left = 3 - n;
    const heroSub = met ? (cel ? "이번 주 목표를 채웠어요. 정말 꾸준했어요!" : `목표 달성 · 이번 주 ${cnt}잔째 마셨어요`)
      : stamped ? `오늘 도장 완료 · ${GOAL - cnt}잔 더 마시면 이번 주 목표예요`
      : `오늘 ${left}가지만 하면 ${cnt + 1}잔째예요`;
    const hero = `<section class="hx${met ? " met" : ""}${cel ? " cel" : ""}" id="week"><div class="hx-t"><b>${met ? "이번 주 목표 달성" : `이번 주 ${GOAL}잔 중 ${cnt}잔`}</b>${st ? `<span class="hx-f">🔥 ${st}일 연속</span>` : ""}</div>
<p class="hx-s">${heroSub}</p><div class="hx-ds">${wk}</div>
<div class="hx-todo"><button type="button" data-go="routine"${n === 3 ? ' class="ok"' : ""}>오늘의 한 잔<span>${n === 3 ? "완료" : `<b>${n}</b>/3`}</span></button><button type="button" data-go="review"${srsN && !due.length ? ' class="ok"' : ""}>오늘의 복습<span>${!srsN ? "아직 없음" : due.length ? `<b>${due.length}</b>개` : "완료"}</span></button></div></section>`;
    root.innerHTML = `<div class="tdg${rvBlock() ? "" : " norv"}">${hero}<section class="rt-card${open === "s" && !r.s ? " hide-en" : ""}" id="routine">
<div class="rt-top"><div class="a-kicker">${esc(SRC_NAME[r.src] || "오늘의 한 잔")} · 5분 루틴</div><span class="rt-prog${n === 3 ? " full" : ""}">${n === 3 ? "도장 완료" : (stamped ? "☕ " : "") + n + " / 3"}</span></div>
<div class="rt-seg" role="tablist" aria-label="연습할 문장 고르기"><button type="button" role="tab" data-src="daily" class="${S.src === "daily" ? "on" : ""}">☕ 오늘의 한 잔</button><button type="button" role="tab" data-seg="sit" class="${S.src !== "daily" ? "on" : ""}">상황별 문장</button></div>
${S.src !== "daily" ? `<div class="rt-goals">${SRCS.map(g => `<button type="button" data-src="${g.id}" class="${S.src === g.id ? "on" : ""}">${g.icon ? `<img src="${g.icon}" alt="" width="26" height="26">` : ""}<span>${esc(g.short)}</span></button>`).join("")}</div>` : ""}
<div class="rt-bar"><i style="width:${pct}%"></i></div><div class="rt-bar-t"><span>${r.src === "daily" ? "오늘의 한 잔 " + set.size + "잔" : SRC_NAME[r.src] + " " + set.size + "문장"} 중 ${got}개 말해 봄</span><span>${pct}%</span></div>
<div class="rt-pbox"><div><p class="rt-phrase">${w.length ? esc(w.join(" ")) + " " : ""}<span class="hl">${esc(last)}</span></p><p class="rt-mean">${esc(r.ko)}</p></div><button type="button" class="rt-spk" data-play="${r.a}" aria-label="발음 듣기"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/></svg></button></div>
<div class="acts">${row("l", "듣기", "원어민 발음 3번 · 1분", r)}${row("s", "말하기", "한국어만 보고 말하면 바로 확인해 줘요 · 2분", r)}${row("r", "복습하기", r.q.ago ? `${r.q.ago}일 전에 말해 본 문장, 기억나요? · 2분` : "방금 배운 문장 한 번 더 · 2분", r)}</div>
<p class="rt-hint">${n === 3 ? `<b class="lbl">쾅!</b> 오늘 도장을 찍었어요. ${st > 1 ? "연속 " + st + "일째예요." : "내일 또 만나요."}` : stamped ? '<b class="lbl">도장</b> 오늘 도장은 이미 찍혔어요. 편하게 한 번 더 연습해요' : '<b class="lbl">도장</b> 듣기·말하기·복습을 다 하면 오늘 도장이 찍혀요'}</p>
${n ? '<button type="button" class="rt-again" data-act="again">↻ 처음부터 한 번 더 연습하기</button>' : ""}
</section>
${rvBlock()}</div>`;
    if (logRoot) logRoot.innerHTML = `<div class="lg-sum"><div><b>${S.stamps.length}</b><span>찍은 도장</span></div><div><b>${st}<em>일</em></b><span>연속 공부</span></div><div><b>${said.length}</b><span>말해 본 문장</span></div></div>
<h2 class="rt-h">말해 본 문장 <small>${said.length}개</small></h2>
${said.length ? '<div class="acts rt-said">' + said.slice(0, saidAll ? 30 : 3).map(x => `<button type="button" class="act" data-play="${x.a}"><span class="act-ic">▶</span><span class="act-t"><b>${esc(x.en)}</b><small>${esc(x.ko)} · ${ago(x.d) ? ago(x.d) + "일 전" : "오늘"}</small></span></button>`).join("") + (said.length > 3 ? `<button type="button" class="rt-more" data-said="1">${saidAll ? "접기" : "전체 보기 · " + said.length + "개"}</button>` : "") + "</div>" : '<p class="rt-sub">루틴에서 듣고 말해 본 문장이 여기에 모여요.</p>'}
${installCard()}`;
    tabCounts();
    document.dispatchEvent(new Event("ky-routine"));
  }
  let deferred = null;
  addEventListener("beforeinstallprompt", e => { e.preventDefault(); deferred = e; render(); });
  let guide = null;
  const SHARE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12M7 8l5-5 5 5"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>';
  function installCard() {
    if (matchMedia("(display-mode: standalone)").matches || navigator.standalone) return "";
    const ua = navigator.userAgent, ios = /iPhone|iPad|iPod/i.test(ua) || (navigator.maxTouchPoints > 1 && /Macintosh/.test(ua));
    const inapp = /KAKAOTALK|Instagram|FBAN|FBAV|NAVER|Line\//i.test(ua);
    const g = guide || (/Android/i.test(ua) ? "android" : "ios");
    const mobile = /Android|iPhone|iPad|iPod|Mobile/i.test(ua) || ios;
    if (mobile) return "";  // 휴대폰은 내 공부방 맨 위 '앱으로 쓰면 더 편해요' 카드가 같은 역할 (중복 방지)
    const steps = {
      ios: [["Safari로 열기", "카톡·인스타 안이라면 오른쪽 아래 ⋯ → <b>Safari로 열기</b>"], ["공유 버튼 누르기", "화면 아래 가운데 " + SHARE + " 버튼 (주소창 옆에 있을 수도 있어요)"], ["홈 화면에 추가", "메뉴를 위로 올려 <b>홈 화면에 추가</b> → 오른쪽 위 <b>추가</b>"]],
      android: [["Chrome으로 열기", "카톡·인스타 안이라면 ⋮ → <b>다른 브라우저로 열기</b>"], ["⋮ 메뉴 누르기", "Chrome 오른쪽 위 <b>⋮</b> (삼성 인터넷은 아래 <b>☰</b>)"], ["홈 화면에 추가", "<b>홈 화면에 추가</b> 또는 <b>앱 설치</b> → <b>설치</b> (삼성 인터넷은 <b>현재 페이지 추가 → 홈 화면</b>)"]]
    }[g];
    return `<div class="rt-install"><div class="rt-in-top"><img src="${D.phone || ""}" alt="" width="40" height="40"><div><b>홈 화면에 추가하면 내 공부방이 앱처럼 열려요</b><p>${inapp ? "지금은 앱 안 브라우저라 추가가 안 돼요. 1번부터 따라 해 주세요." : "아이콘을 누르면 바로 오늘의 루틴으로 와요."}</p></div></div>
<div class="rt-in-tabs"><button data-guide="ios" class="${g === "ios" ? "on" : ""}">아이폰</button><button data-guide="android" class="${g === "android" ? "on" : ""}">안드로이드</button>${deferred && !inapp ? `<button class="rt-in-go" data-act="install">${mobile ? "홈 화면에 추가하기" : "PC 홈 화면 추가"}</button>` : ""}</div>
<ol class="rt-in-steps">${steps.map(([t, d]) => `<li><div><strong class="st-t">${t}</strong><span>${d}</span></div></li>`).join("")}</ol></div>`;
  }
  const onClick = ev => {
    const b = ev.target.closest("button"); if (!b) return;
    const r = S.days[TODAY];
    if (b.dataset.go) { document.getElementById(b.dataset.go)?.scrollIntoView({ block: "start", behavior: "smooth" }); return; }
    if (b.dataset.guide) { guide = b.dataset.guide; render(); return; }
    if (b.dataset.said) { saidAll = !saidAll; render(); return; }
    if (b.dataset.rv) {
      const v = dueList()[0]; if (!v) return;
      if (b.dataset.rv === "show") { rvShow = true; render(); if (v.a) play(v.a); ga("review_show"); return; }
      if (b.dataset.rv === "ok") { v.st = Math.min(v.st + 1, IV.length - 1); v.due = DAY + IV[v.st]; ga("review_ok", { st: v.st }); }
      if (b.dataset.rv === "again") { v.st = 0; v.due = DAY + 1; ga("review_again"); }
      rvShow = false; save(); render(); return;
    }
    if (b.dataset.seg) { if (S.src === "daily") { S.src = S.lastGoal && POOL[S.lastGoal] ? S.lastGoal : (SRCS[0] || {}).id || "daily"; open = null; save(); render(); } return; }
    if (b.classList.contains("ks-mic") || b.classList.contains("ks-done")) {
      const box = b.closest(".ks"), win = () => { r.s = 1; learn(r); save(); if (window.KY_SAY) KY_SAY.spoke(); setTimeout(() => { open = null; render(); }, 1500); };
      if (b.classList.contains("ks-done")) { box.classList.add("ok"); box.querySelector(".ks-t").innerHTML = "<b>잘했어요!</b><small>다음은 복습이에요</small>"; win(); return; }
      if (!window.KY_SAY) return;
      box.querySelector(".ks-t").innerHTML = '<b>듣고 있어요…</b><small>"' + esc(r.en) + '" 하고 말해 보세요</small>';
      KY_SAY.listen(box, r.en, (sc, heard) => KY_SAY.result(box, sc, heard, win));
      return;
    }
    if (b.dataset.src) { if (b.dataset.src !== "daily") S.lastGoal = b.dataset.src; if (S.src !== b.dataset.src) { S.src = b.dataset.src; open = null; save(); ga("goal_pick", { goal: S.src, from: "notes" }); render(); } return; }
    if (b.dataset.step) { open = open === b.dataset.step ? "" : b.dataset.step; render(); return; }
    if (b.dataset.play) {
      // 말해 본 문장: 누르면 ❚❚로 바뀌고 줄 색이 바뀌어 재생 중인 걸 알 수 있게, 다시 누르면 멈춤
      const row = b.closest(".rt-said") ? b : null;
      const reset = x => { x.classList.remove("playing"); const i = x.querySelector(".act-ic"); if (i) i.innerHTML = "▶"; x.setAttribute("aria-label", "재생"); };
      if (row && row.classList.contains("playing")) { if (cur) cur.pause(); reset(row); return; }
      document.querySelectorAll(".rt-said .act.playing").forEach(reset);
      if (row) { row.classList.add("playing"); row.querySelector(".act-ic").innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" fill="currentColor"/></svg>'; row.setAttribute("aria-label", "멈춤"); }
      play(b.dataset.play, 1, 1, () => { if (row) reset(row); });
      return;
    }
    if (b.dataset.q !== undefined) {
      if (b.dataset.q === r.q.en) { b.classList.add("right"); r.r = 1; save(); play(r.q.a); open = null; setTimeout(render, 900); }
      else { b.classList.add("wrong"); b.disabled = true; }
      return;
    }
    const act = b.dataset.act;
    if (act === "again") { r.l = r.s = r.r = 0; if (r.q) r.q.done = 0; open = "l"; save(); render(); document.getElementById("routine")?.scrollIntoView({ block: "start", behavior: "smooth" }); return; }
    if (act === "listen") { b.textContent = "듣는 중…"; play(r.a, 1, 3, () => { r.l = 1; learn(r); save(); open = null; render(); }); }
    if (act === "slow") play(r.a, .75, 1);
    if (act === "reveal") { const c = document.getElementById("routine"); if (c) c.classList.remove("hide-en"); }
    if (act === "reveal" || act === "said") {
      const box = document.getElementById("rt-reveal"); box.hidden = false;
      box.innerHTML = `<b>${esc(r.en)}</b><button type="button" class="rt-spk" data-play="${r.a}" aria-label="원어민 발음 듣기">${SPK}</button>`;
      if (act === "said") { r.s = 1; learn(r); save(); open = null; setTimeout(render, 1300); }
    }
    if (act === "rec") record(b, r);
    if (act === "install" && deferred) { deferred.prompt(); deferred.userChoice.finally(() => { deferred = null; render(); }); }
  };
  root.addEventListener("click", onClick);
  if (logRoot) logRoot.addEventListener("click", onClick);
  async function record(b, r) {
    let stream;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); } catch (e) { b.textContent = "마이크를 쓸 수 없어요"; b.disabled = true; return; }
    const ch = [], mr = new MediaRecorder(stream);
    mr.ondataavailable = e => ch.push(e.data);
    mr.onstop = () => {
      stream.getTracks().forEach(t => t.stop());
      const url = URL.createObjectURL(new Blob(ch, { type: mr.mimeType }));
      const box = document.getElementById("rt-reveal"); box.hidden = false;
      box.innerHTML = `<b>${esc(r.en)}</b><button class="rt-b d" data-play="${url}">▶ 내 목소리</button><button class="rt-b" data-play="${r.a}">▶ 원어민</button><p class="rt-sub">번갈아 들어 보고, 다르면 한 번 더 말해 보세요.</p>`;
      r.s = 1; learn(r); save(); b.textContent = "● 다시 녹음"; b.dataset.act = "rec";
      const row = root.querySelector('[data-step="s"]'); if (row) { row.classList.add("rt-done"); row.querySelector(".act-r").innerHTML = '<span class="rt-ok">✓</span>'; }
    };
    mr.start(); b.textContent = "■ 다 말했으면 눌러서 끝내기"; b.dataset.act = "";
    const stop = () => { b.removeEventListener("click", stop); if (mr.state === "recording") mr.stop(); };
    setTimeout(() => b.addEventListener("click", stop), 0);
    setTimeout(stop, 8000);
  }
  { const h = location.hash.slice(1), t = TAB_OF[h]; if (t && t !== "today") showTab(t);
    if (/^(routine|review|backup)$/.test(h)) setTimeout(() => document.getElementById(h)?.scrollIntoView({ block: "start" }), 50); }
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  render();
  // 말하기 도구(app.js)가 늦게 준비되면 한 번 더 그려서 마이크 버튼이 나오게
  if (!window.KY_SAY) addEventListener("load", () => { if (window.KY_SAY) render(); });
})();
