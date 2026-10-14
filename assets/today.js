/* 카페인영어 · 오늘의 5분 (가입 없이, 기록은 이 기기에만) */
(function () {
  const root = document.getElementById("today-app");
  if (!root) return;
  const D = JSON.parse(document.getElementById("page-data").textContent || "{}");
  const POOL = D.pool || {}, GOALS = D.goals || [];
  const KEY = "ky_today_v1";
  let S;
  try { S = JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { S = {}; }
  S.days = S.days || {}; S.learned = S.learned || []; S.ptr = S.ptr || {};
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const ymd = d => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  const TODAY = ymd(new Date());
  const daysAgo = s => Math.round((new Date(TODAY) - new Date(s)) / 864e5);
  const goalOf = id => GOALS.find(g => g.id === id);
  const done = r => r && r.l && r.s && r.r;
  let tab = "today";

  // ---------- 오늘 기록 만들기 ----------
  function todayRec() {
    const g = S.goal, pool = POOL[g] || [];
    let r = S.days[TODAY];
    if (!r || r.g !== g) {
      const i = (S.ptr[g] || 0) % pool.length;
      S.ptr[g] = (i + 1) % pool.length;
      r = S.days[TODAY] = { g, i, l: 0, s: 0, r: 0 };
      // 다시 꺼내기: 3일·7일 전 표현 우선, 없으면 예전 표현, 그것도 없으면 오늘 표현
      const old = S.learned.filter(x => x.d !== TODAY && POOL[x.g] && POOL[x.g][x.i]);
      const pick = old.find(x => daysAgo(x.d) === 3) || old.find(x => daysAgo(x.d) === 7) || old[Math.floor(Math.random() * old.length)];
      r.q = pick ? { g: pick.g, i: pick.i, ago: daysAgo(pick.d) } : { g, i, ago: 0 };
      const qp = POOL[r.q.g], opts = [r.q.i];
      while (opts.length < Math.min(4, qp.length)) { const k = Math.floor(Math.random() * qp.length); if (!opts.includes(k)) opts.push(k); }
      r.q.o = opts.sort(() => Math.random() - .5);
      save();
    }
    return r;
  }
  function streak() {
    let n = 0, d = new Date(TODAY);
    if (!done(S.days[TODAY])) d.setDate(d.getDate() - 1);
    while (done(S.days[ymd(d)])) { n++; d.setDate(d.getDate() - 1); }
    return n;
  }
  function learn(r) {
    if (r.l && r.s && !S.learned.some(x => x.d === TODAY && x.g === r.g && x.i === r.i)) S.learned.push({ g: r.g, i: r.i, d: TODAY });
  }

  // ---------- 소리 ----------
  let cur = null;
  function play(src, rate, times, onEnd) {
    if (cur) { cur.pause(); cur = null; }
    let n = 0;
    const a = new Audio(src); a.playbackRate = rate || 1; cur = a;
    a.onended = () => { n++; if (n < (times || 1) && cur === a) setTimeout(() => { a.currentTime = 0; a.play(); }, 600); else if (onEnd) onEnd(); };
    a.play().catch(() => onEnd && onEnd());
  }

  // ---------- 화면 ----------
  function tabs() {
    return '<div class="td-tabs" role="tablist">' + [["today", "오늘의 5분"], ["log", "내 기록"], ["goal", "목표 바꾸기"]]
      .map(([k, t]) => `<button role="tab" class="${tab === k ? "on" : ""}" data-tab="${k}">${t}</button>`).join("") + "</div>";
  }
  function viewGoal(first) {
    return (first ? '<h2 class="td-h">지금 어떤 영어가 필요하세요?</h2><p class="td-sub">고른 목표에 맞춰 매일 5분 루틴을 짜 드려요. 언제든 바꿀 수 있어요.</p>'
      : '<h2 class="td-h">목표 바꾸기</h2><p class="td-sub">지금까지의 기록은 그대로 남아요.</p>')
      + GOALS.map(g => `<button class="td-goal${S.goal === g.id ? " on" : ""}" data-goal="${g.id}"><span class="td-gi" style="background:${g.bg}">${g.icon}</span><span><b>${esc(g.name)}</b><small>${esc(g.desc)}</small></span></button>`).join("")
      + '<p class="td-note">가입 없이 쓰고, 기록은 이 기기의 브라우저에만 저장돼요.</p>';
  }
  function viewToday() {
    const r = todayRec(), it = POOL[r.g][r.i], q = r.q, qi = POOL[q.g][q.i], st = streak();
    const left = 3 - (r.l + r.s + r.r);
    const mic = !!(navigator.mediaDevices && window.MediaRecorder);
    return `<div class="td-top"><span class="td-pill">${esc(goalOf(r.g).name)}</span><span class="td-streak">${st ? "연속 " + st + "일째" : "오늘이 첫날"}</span></div>
<div class="td-step${r.l ? " ok" : ""}"><div class="td-n">${r.l ? "✓" : "1"}</div><div class="td-st">1 · 듣기 (1분)</div>
<div class="td-en">${esc(it.en)}</div><div class="td-ko">${esc(it.ko)}</div>
<div class="td-row"><button class="td-chip d" data-act="listen">▶ 3번 듣기</button><button class="td-chip" data-act="slow">천천히</button><a class="td-chip" href="${it.p}">글로 보기</a></div></div>
<div class="td-step${r.s ? " ok" : ""}"><div class="td-n">${r.s ? "✓" : "2"}</div><div class="td-st">2 · 말하기 (2분)</div>
<div class="td-say">“${esc(it.ko)}”</div><div class="td-ko">방금 들은 문장, 한국어만 보고 소리 내어 말해 보세요</div>
<div class="td-row">${mic ? '<button class="td-chip d" data-act="rec" id="td-rec">● 녹음하고 비교하기</button>' : ""}<button class="td-chip" data-act="reveal">정답 보기</button><button class="td-chip" data-act="said">말해 봤어요</button></div>
<div class="td-reveal" id="td-reveal" hidden></div></div>
<div class="td-step${r.r ? " ok" : ""}"><div class="td-n">${r.r ? "✓" : "3"}</div><div class="td-st">3 · 다시 꺼내기 (2분) · ${q.ago ? q.ago + "일 전에 배운 표현" : "오늘 표현 한 번 더"}</div>
<div class="td-say">“${esc(qi.ko)}”를 영어로?</div>
<div class="td-qz">${q.o.map(k => `<button data-q="${k}"${r.r && k === q.i ? ' class="right"' : ""}>${esc(POOL[q.g][k].en)}</button>`).join("")}</div></div>
<div class="td-stamp${left ? "" : " on"}"><div class="td-c">${left ? "도장" : "쾅!"}</div><div><b>${left ? left + "단계 남았어요" : "오늘 도장 완료!"}</b><span>${left ? "다 하면 오늘 도장이 찍혀요" : "내일 이 시간에 또 만나요. 기록은 '내 기록'에서 볼 수 있어요"}</span></div></div>
${installCard()}`;
  }
  function viewLog() {
    const now = new Date(TODAY), mon = new Date(now); mon.setDate(now.getDate() - ((now.getDay() + 6) % 7));
    let wk = "", cnt = 0, L = 0, Sp = 0, R = 0;
    for (let k = 0; k < 7; k++) {
      const d = new Date(mon); d.setDate(mon.getDate() + k); const s = ymd(d), r = S.days[s];
      if (r) { L += r.l; Sp += r.s; R += r.r; }
      if (done(r)) cnt++;
      wk += `<div class="td-dy${done(r) ? " ok" : ""}${s === TODAY ? " td" : ""}"><i>${done(r) ? "✓" : ""}</i>${"월화수목금토일"[k]}</div>`;
    }
    const mx = Math.max(L, Sp, R, 1);
    const bar = (t, v) => `<div class="td-bar"><p>${t}<span>${v}회</span></p><s><i style="width:${Math.round(v / mx * 100)}%"></i></s></div>`;
    const tip = !L && !Sp && !R ? "이번 주 기록이 아직 없어요. 오늘의 5분부터 시작해 볼까요?"
      : Sp < L ? "듣기에 비해 말하기가 적었어요. 내일은 말하기부터 해 볼까요?" : R < L ? "다시 꺼내기를 챙기면 오래 기억에 남아요." : "균형 좋게 하고 있어요. 이대로만 가요!";
    const said = S.learned.slice().reverse().filter(x => POOL[x.g] && POOL[x.g][x.i]).slice(0, 30);
    return `<div class="td-week">${wk}</div>
<div class="td-big"><div><b>${cnt}일</b><span>이번 주 도장</span></div><div><b>${streak()}일</b><span>연속 기록</span></div><div><b>${S.learned.length}개</b><span>말해 본 문장</span></div></div>
<h3 class="td-sec">이번 주 균형</h3>${bar("듣기", L)}${bar("말하기", Sp)}${bar("다시 꺼내기", R)}<p class="td-ko" style="margin-top:6px">${tip}</p>
<h3 class="td-sec">이제 말해 본 문장</h3>${said.length ? '<div class="td-can">' + said.map(x => { const it = POOL[x.g][x.i]; return `<button data-play="${it.a}"><b>${esc(it.en)}</b><span>${esc(it.ko)} · ${daysAgo(x.d) ? daysAgo(x.d) + "일 전" : "오늘"}</span></button>`; }).join("") + "</div>" : '<p class="td-ko">오늘의 5분에서 듣고 말한 문장이 여기에 모여요.</p>'}
<p class="td-note">기록은 이 기기의 브라우저에만 저장돼요. 다른 기기에서는 따로 쌓여요.</p>`;
  }
  // ---------- 홈 화면 추가 ----------
  let deferred = null;
  addEventListener("beforeinstallprompt", e => { e.preventDefault(); deferred = e; render(); });
  function installCard() {
    const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
    if (standalone) return "";
    const ua = navigator.userAgent, ios = /iPhone|iPad|iPod/i.test(ua), inapp = /KAKAOTALK|Instagram|FBAN|FBAV|NAVER|Line\//i.test(ua);
    let how;
    if (inapp) how = "카톡·인스타 안에서는 홈 화면에 추가할 수 없어요. 오른쪽 위(또는 아래) <b>⋯ 메뉴 → 다른 브라우저로 열기</b>를 누른 뒤 추가해 주세요.";
    else if (deferred) how = '<button class="td-chip d" data-act="install">홈 화면에 추가하기</button>';
    else if (ios) how = "Safari 아래쪽 <b>공유 버튼(□↑) → 홈 화면에 추가</b>를 누르면 앱처럼 바로 열려요.";
    else how = "브라우저 오른쪽 위 <b>⋮ 메뉴 → 홈 화면에 추가(앱 설치)</b>를 누르면 앱처럼 바로 열려요.";
    return `<div class="td-install"><b>홈 화면에 추가하면 내일 바로 열려요</b><p>${how}</p></div>`;
  }

  function render() {
    if (!S.goal) { root.innerHTML = viewGoal(true); return; }
    root.innerHTML = tabs() + (tab === "goal" ? viewGoal(false) : tab === "log" ? viewLog() : viewToday());
  }
  root.addEventListener("click", ev => {
    const b = ev.target.closest("button"); if (!b) return;
    if (b.dataset.tab) { tab = b.dataset.tab; render(); return; }
    if (b.dataset.goal) { S.goal = b.dataset.goal; save(); tab = "today"; render(); scrollTo({ top: root.offsetTop - 90 }); return; }
    if (b.dataset.play) { play(b.dataset.play); return; }
    const r = S.days[TODAY], it = r && POOL[r.g][r.i];
    if (b.dataset.q !== undefined && r) {
      if (+b.dataset.q === r.q.i) { b.classList.add("right"); r.r = 1; save(); play(POOL[r.q.g][r.q.i].a); setTimeout(render, 900); }
      else { b.classList.add("wrong"); b.disabled = true; }
      return;
    }
    const act = b.dataset.act;
    if (act === "listen") { b.textContent = "듣는 중…"; play(it.a, 1, 3, () => { r.l = 1; learn(r); save(); render(); }); }
    if (act === "slow") play(it.a, .75, 1);
    if (act === "reveal" || act === "said") {
      const box = document.getElementById("td-reveal");
      box.hidden = false; box.innerHTML = `<b>${esc(it.en)}</b><button class="td-chip" data-play="${it.a}">▶ 원어민 발음</button>`;
      if (act === "said") { r.s = 1; learn(r); save(); setTimeout(render, 1200); }
    }
    if (act === "rec") record(b, r, it);
    if (act === "install" && deferred) { deferred.prompt(); deferred.userChoice.finally(() => { deferred = null; render(); }); }
  });
  async function record(b, r, it) {
    let stream;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); } catch (e) { b.textContent = "마이크를 쓸 수 없어요"; b.disabled = true; return; }
    const ch = [], mr = new MediaRecorder(stream);
    mr.ondataavailable = e => ch.push(e.data);
    mr.onstop = () => {
      stream.getTracks().forEach(t => t.stop());
      const url = URL.createObjectURL(new Blob(ch, { type: mr.mimeType }));
      const box = document.getElementById("td-reveal"); box.hidden = false;
      box.innerHTML = `<b>${esc(it.en)}</b><button class="td-chip d" data-play="${url}">▶ 내 목소리</button><button class="td-chip" data-play="${it.a}">▶ 원어민</button><p class="td-ko">두 소리를 번갈아 들어 보고, 다르면 한 번 더 말해 보세요.</p>`;
      r.s = 1; learn(r); save();
      b.textContent = "● 다시 녹음"; b.disabled = false;
      const st2 = document.querySelectorAll(".td-step")[1]; if (st2) st2.classList.add("ok");
    };
    mr.start(); b.textContent = "■ 말한 뒤 눌러서 끝내기"; b.dataset.act = "";
    b.onclick = () => { b.onclick = null; b.dataset.act = "rec"; if (mr.state === "recording") mr.stop(); };
    setTimeout(() => { if (mr.state === "recording") { b.onclick = null; b.dataset.act = "rec"; mr.stop(); } }, 8000);
  }
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  render();
})();
