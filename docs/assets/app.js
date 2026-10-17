/* 카페인영어 CafeInEnglish — 퀴즈 · 오답노트 · 필사 · 출력
   페이지마다 <script id="page-data" type="application/json"> 에 데이터가 들어 있어요. */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const L = ["A", "B", "C", "D", "E"];
  const DATA = (() => { try { return JSON.parse($("#page-data").textContent); } catch (e) { return {}; } })();

  /* ---------- 저장소 (방문자 브라우저에만 저장, 로그인 없음) ---------- */
  function makeStore(K) {
    let mem = {};
    const load = () => { try { const r = localStorage.getItem(K); return r ? JSON.parse(r) : {}; } catch (e) { return mem; } };
    const save = d => { mem = d; try { localStorage.setItem(K, JSON.stringify(d)); } catch (e) {} };
    return { load, save };
  }
  const wrongDB = makeStore("cafein_wrong_v1");
  const copyDB = makeStore("cafein_copy_v1");
  const wrong = {
    all: () => wrongDB.load(),
    add(id, snap, picked) { const d = wrongDB.load(); const c = d[id]; d[id] = { ...snap, picked, count: (c ? c.count : 0) + 1, at: Date.now() }; wrongDB.save(d); },
    remove(id) { const d = wrongDB.load(); delete d[id]; wrongDB.save(d); },
    clear() { wrongDB.save({}); }
  };

  function toast(msg) {
    let t = $("#toast");
    if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; document.body.appendChild(t); }
    t.textContent = msg; t.classList.add("show"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 1800);
  }
  function routineDot() {
    let r = null, st = false;
    try { const s = JSON.parse(localStorage.getItem("ky_today_v1")) || {}, k = new Date((Math.floor((Date.now() / 1000 + 9 * 3600) / 86400)) * 864e5).toISOString().slice(0, 10); r = (s.days || {})[k]; st = (s.stamps || []).indexOf(k) > -1; } catch (e) {}
    const room = $(".room"); if (!room) return;
    let d = $(".rt-dot", room);
    const need = !st && !(r && r.l && r.s && r.r);
    if (need && !d) { d = document.createElement("span"); d.className = "rt-dot"; d.title = "오늘의 한 잔 루틴이 남았어요"; room.appendChild(d); }
    if (!need && d) d.remove();
  }
  document.addEventListener("ky-routine", routineDot);
  // 오른쪽 아래 + 버튼: 스크롤하는 동안 숨기고, 멈추면 다시 보이기 (메뉴가 열려 있을 땐 그대로)
  (function fabScroll() {
    const fab = $("#fab"); if (!fab) return;
    let t;
    addEventListener("scroll", () => {
      const m = $(".fab-main", fab); if (m && m.getAttribute("aria-expanded") === "true") return;
      fab.classList.add("fab-hide"); clearTimeout(t); t = setTimeout(() => fab.classList.toggle("fab-hide", top()), 600);
    }, { passive: true });
    // 폰 첫 화면(맨 위)에서는 버튼을 가리지 않게 숨겨 두고, 조금이라도 내리면 나타나요
    const top = () => innerWidth < 600 && scrollY < 120;
    fab.classList.toggle("fab-hide", top());
  })();
  // 홈: 루틴을 해 본 사람은 '내 진도' 카드, 처음이면 목표 고르기
  (function homeGoal() {
    const gp = $("#gp"); if (!gp) return;
    window.__gpOrig = gp.outerHTML;
    gp.addEventListener("click", e => { const a = e.target.closest("[data-goal]"); if (a && window.gtag) gtag("event", "goal_pick", { goal: a.dataset.goal, from: "home" }); });
    let s = null; try { s = JSON.parse(localStorage.getItem("ky_today_v1")) || null; } catch (e) {}
    const p = s && s.prog; if (!p || !(s.learned || []).length) return;
    const ICON = { talk: "speech-balloon", travel: "airplane", work: "laptop", life: "world-map", daily: "hot-beverage" }[p.src] || "hot-beverage";
    const img = $(".gp-c img", gp).getAttribute("src").replace(/icons\/[a-z-]+\.webp/, "icons/" + ICON + ".webp");
    const pct = p.t ? Math.round(p.n / p.t * 100) : 0;
    const todayKey = new Date((Math.floor((Date.now() / 1000 + 9 * 3600) / 86400)) * 864e5).toISOString().slice(0, 10);
    const doneToday = p.day === todayKey && p.done;
    gp.innerHTML = `<a class="gp-me" href="/notes/#routine"><img src="${img}" alt=""><span class="gp-t"><b>${esc(p.name)}${p.streak ? " · 연속 " + p.streak + "일" : ""}</b><small>${doneToday ? "오늘 도장 완료 · " : "오늘 말할 문장이 기다려요 · "}${p.t}개 중 ${p.n}개 말해 봄</small><span class="rt-bar"><i style="width:${pct}%"></i></span></span><span class="gp-go">${doneToday ? "기록 보기 ✓" : p.n ? "이어서 말하기 →" : "첫 문장 시작 →"}</span></a><button type="button" class="gp-sw">다른 목표 고르기</button>`;
    const html0 = gp.dataset.orig;
    $(".gp-sw", gp).onclick = () => { location.href = "/#gp"; gp.outerHTML = window.__gpOrig; };
  })();
  setTimeout(routineDot, 0);
  function updateBadge() {
    const n = Object.keys(wrong.all()).length;
    const b = $("#nav-badge"); if (b) { b.hidden = !n; b.textContent = n; }
    $$(".js-notes-count").forEach(x => { x.textContent = n || ""; x.dataset.n = n; });
    if (typeof alignNav === "function") alignNav();
  }

  /* ---------- 퀴즈 엔진 (글 퀴즈 / 오답 다시 풀기 공용) ---------- */
  function runQuiz(el, items, opt) {
    let i = 0, score = 0, graduated = 0, newWrong = 0;
    const review = opt.mode === "review";

    function render() {
      const d = items[i], n = items.length;
      el.innerHTML = `<div class="cq">
        <div class="cq-head"><span class="chip ${review ? "tip" : "expr"}">${review ? "오답 다시 풀기" : "오늘의 퀴즈"}</span><span class="cq-step">${i + 1} / ${n}</span></div>
        <div class="cq-bar"><i style="width:${(i / n) * 100}%"></i></div>
        <p class="cq-q">${esc(d.q)}</p><p class="cq-sub">${esc(d.sub || "")}</p>
        <div class="cq-opts">${d.options.map((t, k) => `<button class="cq-opt" data-k="${k}"><b>${L[k]}</b><span>${esc(t)}</span></button>`).join("")}</div>
        <div class="fb"></div></div>`;
      $$(".cq-opt", el).forEach(b => b.onclick = () => pick(+b.dataset.k));
    }

    function pick(k) {
      const d = items[i], right = k === d.answer;
      $$(".cq-opt", el).forEach((b, j) => { b.disabled = true; b.classList.add(j === d.answer ? "ok" : j === k ? "bad" : "dim"); });
      let extra = "";
      if (right) {
        score++;
        if (review) { wrong.remove(d.id); graduated++; extra = `<div class="saved" style="color:var(--ok)">오답노트에서 졸업했어요!</div>`; }
      } else {
        const snap = { q: d.q, sub: d.sub, options: d.options, answer: d.answer, explain: d.explain, mnemonic: d.mnemonic, tag: d.tag,
          postTitle: d.postTitle || DATA.title, postUrl: d.postUrl || DATA.url, cat: d.cat || DATA.cat, catName: d.catName || DATA.catName };
        wrong.add(d.id, snap, k); newWrong++;
        extra = `<div class="saved">오답노트에 저장했어요. 나중에 다시 풀 수 있어요.</div>`;
      }
      updateBadge();
      const last = i === items.length - 1;
      $(".fb", el).innerHTML = `
        <div class="cq-fb ${right ? "ok" : "bad"}">
          <strong>${right ? "정답이에요!" : `아쉬워요! 정답은 ${L[d.answer]}`}</strong>${esc(d.explain)}
          <div class="mn"><b class="lbl">연상법</b> ${esc(d.mnemonic)}</div>${extra}
        </div>
        <button class="btn primary next" style="margin-top:12px">${last ? "결과 보기" : "다음 문제 →"}</button>`;
      const nx = $(".next", el);
      nx.onclick = () => { i++; i < items.length ? render() : result(); };
      nx.focus({ preventScroll: true });
    }

    function result() {
      const n = items.length, perfect = score === n;
      if (review) {
        const left = Object.keys(wrong.all()).length;
        el.innerHTML = `<div class="cq"><div class="cq-result">
          
          <div class="cq-score">${graduated}개 졸업!</div>
          <p class="cq-msg">${left ? `아직 ${left}개가 남았어요. 연상법을 한 번 더 읽고 다시 도전해 보세요.` : "오답노트를 모두 졸업했어요. 대단해요!"}</p>
          <div class="cq-cta">
            <a class="btn primary" href="/notes/">오답노트로 돌아가기</a>
            <a class="btn ghost" href="/">새 표현 배우러 가기</a>
            ${DATA.kakao ? `<a class="btn kakao" href="${DATA.kakao}" target="_blank" rel="noopener">매일 아침 표현 하나, 카톡으로 받기<img class="kk-ic" src="/assets/kakao-talk.png" alt="" width="24" height="22"></a>` : ""}
          </div></div></div>`;
        return;
      }
      const links = (DATA.links || []).map(l => `<a href="${l.href}"><span class="en">${esc(l.en || l.label)}</span><span class="ko">${esc(l.ko || "")}</span><span class="ar" aria-hidden="true">→</span></a>`).join("");
      el.innerHTML = `<div class="cq"><div class="cq-result">
        
        <div class="cq-score">${n}문제 중 ${score}개 정답</div>
        <p class="cq-msg">${perfect ? "완벽해요! 이제 이 표현은 완전히 내 거예요." : `틀린 ${newWrong}문제는 오답노트에 모아뒀어요. 연상법으로 다시 복습해 보세요.`}</p>
        <div class="cq-cta">
          ${newWrong ? `<a class="btn primary" href="/notes/">내 공부방에서 복습하기 (${Object.keys(wrong.all()).length})</a>` : ""}
          ${links ? `<p class="nx-h">NEXT · 이어서 배우기</p><div class="nx">${links}</div>` : ""}
          ${DATA.kakao ? `<a class="btn kakao" href="${DATA.kakao}" target="_blank" rel="noopener">매일 아침 표현 하나, 카톡으로 받기<img class="kk-ic" src="/assets/kakao-talk.png" alt="" width="24" height="22"></a>` : ""}
        </div>
        <button class="btn danger again">다시 풀어보기</button>
      </div></div>`;
      $(".again", el).onclick = () => { i = 0; score = 0; newWrong = 0; render(); };
    }
    render();
  }

  /* ---------- 오답노트 페이지 ---------- */
  function renderNotes(root) {
    const data = wrong.all();
    const ids = Object.keys(data).sort((a, b) => data[b].count - data[a].count || data[b].at - data[a].at);
    if (!ids.length) {
      root.innerHTML = `<div class="empty"><p>오답노트가 비어 있어요.<br>퀴즈에서 틀린 문제가 여기에 자동으로 모여요.</p></div>
        <a class="btn primary" href="/">퀴즈 풀러 가기</a>`;
      return;
    }
    const tagCount = {}, tagUrl = {};
    ids.forEach(id => { const t = data[id].tag || "기타"; tagCount[t] = (tagCount[t] || 0) + data[id].count; tagUrl[t] = data[id].postUrl; });
    const weak = Object.entries(tagCount).sort((a, b) => b[1] - a[1])[0][0];
    const total = ids.reduce((s, id) => s + data[id].count, 0);
    root.innerHTML = `
      <div class="stats">
        <div class="stat"><div class="n">${ids.length}</div><div class="l">남은 오답</div></div>
        <div class="stat"><div class="n">${total}</div><div class="l">누적 틀린 횟수</div></div>
        <div class="stat"><div class="n">${esc(weak)}</div><div class="l">약한 유형</div></div>
      </div>
      <div class="weak"><b>'${esc(weak)}'</b> 문제를 가장 자주 틀렸어요. ${tagUrl[weak] ? `<a href="${tagUrl[weak]}">관련 글 다시 보기 →</a>` : ""}</div>
      <button class="btn primary retry">오답만 다시 풀기 (${ids.length}문제)</button>
      <div class="review"></div>
      <div class="note-list">${ids.map(id => {
        const d = data[id];
        return `<div class="note">
          <div class="note-top"><span><span class="chip ${esc(d.cat || "expr")}">${esc(d.catName || "")}</span><span class="chip ${esc(d.cat || "expr")}">${esc(d.tag || "")}</span></span><span>${d.count}번 틀림</span></div>
          <h3>${esc(d.q)}${d.sub && d.sub.includes("___") ? `<br><span style="font-weight:400">${esc(d.sub)}</span>` : ""}</h3>
          <div class="ans">
            <div class="mine"><b>내가 고른 답</b> ${esc(d.options[d.picked])}</div>
            <div class="right"><b>정답</b> ${esc(d.options[d.answer])}</div>
          </div>
          <details><summary>왜 틀렸을까? 복기하기</summary>
            <div class="why">${esc(d.explain)}</div>
            <div class="memo"><b class="lbl">연상법</b> ${esc(d.mnemonic)}</div>
          </details>
          <a class="src" href="${d.postUrl}">원래 글 다시 보기 · ${esc(d.postTitle)}</a>
        </div>`; }).join("")}</div>
      <button class="btn danger clear">오답노트 전체 비우기</button>`;
    $(".retry", root).onclick = () => {
      $(".retry", root).hidden = true; $(".note-list", root).hidden = true;
      runQuiz($(".review", root), ids.map(id => ({ id, ...data[id] })), { mode: "review" });
    };
    $(".clear", root).onclick = () => { wrong.clear(); updateBadge(); renderNotes(root); toast("오답노트를 비웠어요"); };
  }

  /* ---------- 사유의 문장: 필사 · 빈칸 복기 · 나의 한 줄 ---------- */
  const norm = w => w.toLowerCase().replace(/[’‘]/g, "'").replace(/[^a-z0-9']/g, "");
  const copy = {
    all: () => copyDB.load(),
    rec(id, snap, patch) { const d = copyDB.load(); const c = d[id] || { count: 0, best: 0 }; d[id] = { ...c, ...snap, ...patch(c), at: Date.now() }; copyDB.save(d); }
  };

  function copyMode(pane, q, id, snap) {
    pane.innerHTML = `<textarea placeholder="위 영어 문장을 보면서 그대로 따라 써 보세요"></textarea>
      <div class="row"><button class="btn primary check">채점하기</button></div><div class="res"></div>`;
    $(".check", pane).onclick = () => {
      const src = q.en.split(/\s+/), a = src.map(norm);
      const b = $("textarea", pane).value.split(/\s+/).map(norm).filter(Boolean);
      const dp = Array.from({ length: a.length + 1 }, () => Array(b.length + 1).fill(0));
      for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--)
        dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
      const hit = new Set(); let i = 0, j = 0;
      while (i < a.length && j < b.length) { if (a[i] === b[j]) { hit.add(i); i++; j++; } else if (dp[i + 1][j] >= dp[i][j + 1]) i++; else j++; }
      const acc = Math.round(hit.size / a.length * 100), extra = Math.max(0, b.length - hit.size);
      copy.rec(id, snap, c => ({ count: c.count + 1, best: Math.max(c.best, acc) }));
      $(".res", pane).innerHTML = `
        <div class="diff">${src.map((w, k) => `<span class="w ${hit.has(k) ? "hit" : "miss"}">${esc(w)}</span>`).join(" ")}</div>
        <div class="acc">${acc === 100 ? "완벽해요! 필사 노트에 담았어요." : `정확도 ${acc}% · 빨간 단어를 다시 확인해 보세요${extra ? ` (불필요한 단어 ${extra}개)` : ""}`}</div>`;
    };
  }

  function blankMode(pane, q) {
    const left = [...q.blanks];
    const parts = q.en.split(/(\s+)/).map(tok => {
      const k = left.findIndex(bw => norm(tok) === bw);
      if (k < 0) return esc(tok);
      const ans = left.splice(k, 1)[0];
      const tail = tok.slice(tok.toLowerCase().indexOf(ans) + ans.length);
      return `<input class="blank" data-a="${ans}" autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="빈칸">${esc(tail)}`;
    });
    pane.innerHTML = `<div class="blanks">${parts.join("")}</div>
      <div class="row"><button class="btn primary check">확인하기</button><button class="btn ghost hint">힌트 (첫 글자)</button></div><div class="res"></div>`;
    const inputs = $$("input.blank", pane);
    $(".hint", pane).onclick = () => inputs.forEach(n => { if (!n.value) n.placeholder = n.dataset.a[0] + "…"; });
    $(".check", pane).onclick = () => {
      let ok = 0;
      inputs.forEach(n => { const g = norm(n.value) === n.dataset.a; n.classList.toggle("ok", g); n.classList.toggle("bad", !g); if (g) ok++; });
      $(".res", pane).innerHTML = `<div class="acc">${ok === inputs.length ? "전부 떠올렸어요! 이제 이 문장은 내 거예요." :
        `${inputs.length}개 중 ${ok}개 · 빨간 칸을 다시 떠올려 보세요 (정답: ${inputs.filter(n => !n.classList.contains("ok")).map(n => n.dataset.a).join(", ")})`}</div>`;
    };
  }

  function initThink() {
    const rec = copy.all();
    $$(".quote[data-i]").forEach(card => {
      const q = DATA.quotes[+card.dataset.i], id = card.dataset.id, pane = $(".pane", card);
      const snap = { en: q.en, ko: q.ko, title: DATA.title, speaker: DATA.speaker, url: DATA.url };
      const modes = { copy: () => copyMode(pane, q, id, snap), blank: () => blankMode(pane, q) };
      $$(".tabs button", card).forEach(b => b.onclick = () => { $$(".tabs button", card).forEach(x => x.classList.toggle("on", x === b)); modes[b.dataset.mode](); });
      const note = $("textarea.note", card);
      if (rec[id] && rec[id].note) note.value = rec[id].note;
      $(".save-note", card).onclick = () => { copy.rec(id, snap, () => ({ note: note.value.trim() })); toast("나의 한 줄을 저장했어요"); };
      modes.copy();
    });
  }

  function renderCopyNotes(root) {
    const d = copy.all(), ids = Object.keys(d).sort((a, b) => d[b].at - d[a].at);
    $("#copy-count") && ($("#copy-count").textContent = ids.length);
    root.innerHTML = ids.length ? ids.map(id => { const r = d[id]; return `
      <div class="quote">
        <div class="meta"><span>${esc(r.speaker || "")}</span><span>필사 ${r.count || 0}회 · 최고 ${r.best || 0}%</span></div>
        <p class="en">${esc(r.en)}</p><p class="ko">${esc(r.ko)}</p>
        ${r.note ? `<div class="think-box"><b class="lbl">나의 한 줄</b> ${esc(r.note)}</div>` : ""}
        <a class="src" style="font-size:13px;color:var(--muted)" href="${r.url}">다시 필사하기 →</a>
      </div>`; }).join("") :
      `<div class="empty"><p>아직 필사한 문장이 없어요.<br>문장을 따라 쓰면 여기에 나만의 문장집이 쌓여요.</p></div>`;
  }

  /* ---------- 영상: 썸네일 먼저 · 구간 듣기 · 반복 · 속도 · 따라오는 영상 ---------- */
  function initVideo() {
    const box = $(".video-embed[data-vid]"); if (!box) return;
    const slot = $(".video-slot"), facade = $(".v-facade", box), vid = box.dataset.vid;
    let player = null, ready = false, creating = false, started = false, dismissed = false;
    let seg = null, timer = null, rate = 1, queued = null, apiLoading = false;

    // 플레이어 API는 가볍게 미리 받아 두고, 실제 영상(무거운 부분)은 누를 때 불러와요
    function loadAPI() {
      if (apiLoading || (window.YT && YT.Player)) return; apiLoading = true;
      const tag = document.createElement("script"); tag.src = "https://www.youtube.com/iframe_api"; document.head.appendChild(tag);
    }
    const idle = window.requestIdleCallback || (f => setTimeout(f, 1500));
    idle(loadAPI);
    ["pointerdown", "touchstart", "scroll"].forEach(ev => addEventListener(ev, loadAPI, { once: true, passive: true }));

    function create() {
      if (creating) return; creating = true;
      box.classList.add("loading");
      player = new YT.Player("yt", {
        videoId: vid, host: "https://www.youtube.com",
        playerVars: { autoplay: 1, rel: 0, playsinline: 1, modestbranding: 1 },
        events: {
          onReady: () => {
            ready = true; box.classList.remove("loading"); box.classList.add("live");
            player.setPlaybackRate(rate);
            const q = queued; queued = null; q ? q() : player.playVideo();
          },
          onStateChange: ev => { if (ev.data === 1) { started = true; updateFloat(); } }
        }
      });
    }
    function withPlayer(fn) {
      if (ready) return fn();
      queued = fn;
      if (window.YT && YT.Player) create();
      else { loadAPI(); window.onYouTubeIframeAPIReady = create; }
    }
    facade.onclick = () => withPlayer(() => player.playVideo());

    function stopSeg() {
      clearInterval(timer); timer = null; seg = null;
      $$(".sh-play.on").forEach(b => { b.classList.remove("on"); const c = b.querySelector(".cnt"); c && c.remove(); });
    }
    function playSeg(t, end, n, btn) {
      stopSeg();
      seg = { t, end, left: n, btn, since: Date.now() }; btn.classList.add("on");
      const cnt = document.createElement("span"); cnt.className = "cnt"; btn.appendChild(cnt);
      const show = () => { cnt.textContent = n > 1 ? ` ${n - seg.left + 1}/${n}` : ""; };
      show();
      withPlayer(() => {
        if (!seg) return;
        seg.since = Date.now();
        player.setPlaybackRate(rate); player.seekTo(t, true); player.playVideo();
        started = true; updateFloat();
        timer = setInterval(() => {
          if (!seg || Date.now() - seg.since < 700) return;          // 이동 직후엔 시간이 바로 안 바뀌어요
          if (player.getPlayerState() !== 1) return;                 // 재생 중일 때만 셉니다
          const ct = player.getCurrentTime();
          if (ct >= seg.end || ct < seg.t - 1.5) {
            seg.left--;
            if (seg.left > 0) { show(); seg.since = Date.now(); player.seekTo(seg.t, true); player.playVideo(); }
            else { player.pauseVideo(); stopSeg(); }
          }
        }, 150);
      });
    }
    $$(".sh-play").forEach(b => b.onclick = () => {
      if (b.classList.contains("on")) { ready && player.pauseVideo(); stopSeg(); return; }
      playSeg(+b.dataset.t, +b.dataset.end, +b.dataset.n, b);
    });
    $$(".spd").forEach(b => b.onclick = () => {
      rate = +b.dataset.r; $$(".spd").forEach(x => x.classList.toggle("on", x === b));
      if (ready) player.setPlaybackRate(rate);
    });

    // 스크롤해도 영상이 따라오도록 (재생을 시작한 뒤에만)
    let past = false;
    function headerH() { const h = $(".top"); return h ? h.getBoundingClientRect().height : 0; }
    function updateFloat() {
      const on = past && started && !dismissed;
      box.classList.toggle("float", on);
      document.documentElement.style.setProperty("--hdr", headerH() + "px");
      // PC: 본문 영상 자리 크기 그대로 상단에 고정 (위치·너비를 영상 자리에서 가져와요)
      const r = slot.getBoundingClientRect(), st = document.documentElement.style;
      st.setProperty("--vx", r.left + "px"); st.setProperty("--vw", r.width + "px"); st.setProperty("--vh", r.width * 9 / 16 + "px");
      document.documentElement.classList.toggle("v-floating", on);
    }
    const io = new IntersectionObserver(([en]) => {
      past = !en.isIntersecting && en.boundingClientRect.top < 0;
      if (en.isIntersecting) dismissed = false;
      updateFloat();
    }, { rootMargin: `-${Math.round(headerH())}px 0px 0px 0px` });
    io.observe(slot);
    $(".v-close").onclick = () => { dismissed = true; updateFloat(); };
    addEventListener("resize", updateFloat);
    addEventListener("resize", updateFloat);
  }

  /* ---------- 공유 · 링크 복사 ---------- */
  async function copyText(v) {
    try { await navigator.clipboard.writeText(v); return true; } catch (e) {
      const t = document.createElement("textarea"); t.value = v; document.body.appendChild(t); t.select();
      let ok = false; try { ok = document.execCommand("copy"); } catch (e2) {} t.remove(); return ok;
    }
  }
  function initShare() {
    const url = location.origin + location.pathname;
    const title = DATA.title ? `${DATA.title} | 카페인영어` : document.title;
    $$(".js-copylink").forEach(b => b.onclick = async () => { await copyText(url); toast("링크를 복사했어요"); });
    $$(".js-share").forEach(b => b.onclick = async () => {
      if (navigator.share) { try { await navigator.share({ title, url }); } catch (e) {} return; }
      await copyText(url); toast("링크를 복사했어요");
    });
  }

  /* ---------- 예문 원어민 음성 듣기 ----------
     원어민 음성 파일(mp3)이 있으면 그걸 재생하고, 없을 때만 브라우저 영어 음성으로 읽어요.
     같은 버튼을 한 번 더 누르면 천천히(0.75배) 들려줘요. */
  function initSpeak() {
    const files = DATA.audio || {};
    const hasTTS = "speechSynthesis" in window;
    const icon = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/></svg>';
    const audio = new Audio(); audio.preload = "none";
    let curBtn = null;
    const off = () => { $$(".say-btn.on").forEach(x => x.classList.remove("on")); curBtn = null; };
    audio.onended = off;

    // 브라우저 음성: 한국어 음성이 영어를 읽어 깨지지 않도록 영어(미국) 음성을 직접 골라요
    let voice = null;
    const PREF = [/Google US English/i, /Samantha/i, /Ava/i, /Aria.*Natural/i, /Jenny.*Natural/i, /Microsoft (Aria|Jenny|Guy)/i, /Alex/i];
    function pickVoice() {
      if (!hasTTS) return;
      const en = speechSynthesis.getVoices().filter(v => /^en[-_]US/i.test(v.lang));
      const all = en.length ? en : speechSynthesis.getVoices().filter(v => /^en/i.test(v.lang));
      voice = PREF.map(r => all.find(v => r.test(v.name))).find(Boolean) || all.find(v => v.localService) || all[0] || null;
    }
    if (hasTTS) { pickVoice(); speechSynthesis.onvoiceschanged = pickVoice; }

    $$(".ex li .en").forEach(el => {
      const full = el.textContent.replace(/\s+/g, " ").trim();
      const text = full.replace(/→.*$/, "").trim();
      const file = files[full];
      if (!/[a-zA-Z]/.test(text) || (!file && !hasTTS)) return;
      const b = document.createElement("button");
      b.className = "say-btn"; b.type = "button"; b.setAttribute("aria-label", "원어민 발음 듣기"); b.innerHTML = icon;
      let n = 0;
      b.onclick = () => {
        const slow = n++ % 2 === 1;                       // 1번째 보통 · 2번째 천천히 · 3번째 보통 …
        audio.pause(); if (hasTTS) speechSynthesis.cancel();
        $$(".say-btn.on").forEach(x => x.classList.remove("on")); b.classList.add("on"); curBtn = b;
        if (file) {
          if (!audio.src.endsWith(file)) audio.src = file;
          audio.currentTime = 0; audio.playbackRate = slow ? 0.75 : 1;
          if ("preservesPitch" in audio) audio.preservesPitch = true;
          audio.play().catch(off);
        } else {
          const u = new SpeechSynthesisUtterance(text);
          u.lang = "en-US"; if (voice) u.voice = voice; u.rate = slow ? 0.7 : 0.95;
          u.onend = u.onerror = off;
          speechSynthesis.speak(u);
        }
      };
      el.appendChild(b);
    });
  }

  /* ---------- 모바일 상단: '내 공부방' 가운데 = '사유의 문장' 가운데 ---------- */
  function alignNav() {
    const nav = $(".nav"), room = $(".room");
    if (!nav || !room) return;
    room.style.marginRight = "";
    return; // 모바일 메뉴는 CSS로 로고~내 공부방 폭에 맞춰 정렬 (버튼은 움직이지 않음)
    const last = nav.lastElementChild, rg = document.createRange();
    rg.selectNodeContents(last);
    const t = rg.getBoundingClientRect(), r = room.getBoundingClientRect();
    const d = (r.left + r.right) / 2 - (t.left + t.right) / 2;   // >0 이면 버튼을 왼쪽으로
    room.style.marginRight = Math.max(0, d) + "px";
  }


  /* ---------- 목차: 지금 읽고 있는 곳 표시 ---------- */
  function initTocSpy() {
    const links = $$(".toc a[href^='#']");
    if (!links.length) return;
    const ids = [...new Set(links.map(a => a.getAttribute("href").slice(1)))];
    const secs = ids.map(id => document.getElementById(id)).filter(Boolean);
    if (!secs.length) return;
    let cur = null, tick = false, lockUntil = 0;
    function setActive(id) {
      cur = id;
      links.forEach(a => a.parentElement.classList.toggle("on", a.getAttribute("href") === "#" + id));
    }
    // 목차를 누르면 누른 항목을 바로 표시하고, 이동하는 동안은 바뀌지 않게
    links.forEach(a => a.addEventListener("click", () => { setActive(a.getAttribute("href").slice(1)); lockUntil = Date.now() + 900; }));
    function update() {
      tick = false;
      if (Date.now() < lockUntil) return;
      const hdr = ($(".top") ? $(".top").getBoundingClientRect().height : 0) + 40;
      let active = secs[0];
      for (const s of secs) { if (s.getBoundingClientRect().top - hdr <= 0) active = s; else break; }
      if (innerHeight + scrollY >= document.documentElement.scrollHeight - 4) active = secs[secs.length - 1];
      if (active.id !== cur) setActive(active.id);
    }
    addEventListener("scroll", () => { if (!tick) { tick = true; requestAnimationFrame(update); } }, { passive: true });
    addEventListener("resize", update);
    update();
  }


  /* ---------- 홈: 오늘의 한 잔 (한국 날짜 기준 매일 바뀜) ---------- */
  function initDaily() {
    const list = DATA.daily || [];
    if (!list.length || !$("#td-en")) return;
    const it = list[Math.floor((Date.now() / 1000 + 9 * 3600) / 86400) % list.length];
    const w = it.en.split(" "), last = w.pop();
    $("#td-en").innerHTML = (w.length ? esc(w.join(" ")) + " " : "") + `<span class="hl">${esc(last)}</span>`;
    $("#td-en").classList.toggle("long", it.en.length > 16);
    $("#td-ko").textContent = it.ko;
    $("#td-desc").textContent = it.desc || "";
    $("#td-cat").textContent = it.cat;
    $("#td-link").href = it.url;
  }

  /* ---------- 시작 ---------- */
  updateBadge();
  alignNav();
  addEventListener("resize", alignNav);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(alignNav);
  $$(".js-print").forEach(b => b.onclick = () => window.print());
  // 문의 폼 (FormSubmit으로 바로 전송)
  const cf = $("#contact-form");
  if (cf) {
    let kind = $(".cf-chip.on", cf)?.dataset.kind || "기타";
    $$(".cf-chip", cf).forEach(c => c.onclick = () => {
      $$(".cf-chip", cf).forEach(x => { x.classList.toggle("on", x === c); x.setAttribute("aria-pressed", x === c); });
      kind = c.dataset.kind;
    });
    const err = $("#cf-err"), btn = $(".cf-send", cf);
    const fail = m => { err.textContent = m; err.hidden = false; };
    cf.onsubmit = async ev => {
      ev.preventDefault(); err.hidden = true;
      const msg = $("#cf-msg").value.trim(), mail = $("#cf-mail").value.trim();
      if (msg.length < 2) return fail("궁금한 내용을 적어 주세요.");
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) return fail("답장 받을 이메일을 확인해 주세요.");
      if (cf._honey && cf._honey.value) return;
      const to = cf.dataset.to, subject = `[카페인영어 문의] ${kind}`;
      btn.disabled = true; btn.textContent = "보내는 중…";
      try {
        const r = await fetch(`https://formsubmit.co/ajax/${to}`, {
          method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ _subject: subject, _template: "table", _replyto: mail, "문의 유형": kind, "내용": msg, "답장 이메일": mail, "보낸 페이지": location.href })
        });
        const j = await r.json().catch(() => ({}));
        if (!r.ok || String(j.success) === "false") throw new Error("send");
        cf.hidden = true; $("#cf-done").hidden = false;
      } catch (e) {
        btn.disabled = false; btn.textContent = "문의 보내기";
        fail("지금 바로 보내지 못했어요. 잠시 후 한 번만 다시 눌러 주세요.");
      }
    };
  }
  $$(".ct-copy").forEach(b => b.onclick = async () => {
    const v = b.dataset.copy;
    try { await navigator.clipboard.writeText(v); } catch (e) {
      const t = document.createElement("textarea"); t.value = v; document.body.appendChild(t); t.select();
      try { document.execCommand("copy"); } catch (e2) {} t.remove();
    }
    toast("이메일 주소를 복사했어요");
  });

  // 상단 메뉴: 내리면 아래 실선
  const topbar = $(".top");
  if (topbar) { const f = () => topbar.classList.toggle("scrolled", scrollY > 4); f(); addEventListener("scroll", f, { passive: true }); }
  // 카테고리 분류 필터
  $$(".subfilter .sf-b").forEach(b => b.onclick = () => {
    $$(".subfilter .sf-b").forEach(x => x.classList.toggle("on", x === b));
    const v = b.dataset.sub;
    $$(".cat-grid .card").forEach(c => c.classList.toggle("sf-hide", !!v && c.dataset.sub !== v));
  });
  // 홈 전체 아티클 페이지 넘기기
  $$("#pager button").forEach(b => b.onclick = () => {
    $$("#pager button").forEach(x => x.classList.toggle("on", x === b));
    $$("#all-arts .card").forEach(c => c.classList.toggle("pg-hide", c.dataset.pg !== b.dataset.pg));
    const h = $("#all-arts"); if (h) scrollTo({ top: h.getBoundingClientRect().top + scrollY - 120, behavior: "smooth" });
  });
  const fab = $("#fab");
  if (fab) {
    const btn = $(".fab-main", fab);
    const set = open => { fab.classList.toggle("open", open); btn.setAttribute("aria-expanded", open); };
    btn.onclick = e => { e.stopPropagation(); set(!fab.classList.contains("open")); };
    document.addEventListener("click", e => { if (!fab.contains(e.target)) set(false); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") set(false); });
    $$(".fab-item.pending", fab).forEach(a => a.onclick = e => { e.preventDefault(); toast("카카오톡 채널은 곧 열려요"); });
    // 모바일: 내려 읽는 동안엔 숨기고, 조금이라도 올리거나 맨 아래에 닿으면 다시 보여줘요
    let lastY = scrollY;
    addEventListener("scroll", () => {
      const y = scrollY, end = innerHeight + y >= document.body.scrollHeight - 80;
      if (Math.abs(y - lastY) < 8) return;
      fab.classList.toggle("hide", y > lastY && y > 200 && !end);
      lastY = y;
    }, { passive: true });
  }
  initVideo();
  initShare();
  initTocSpy();
  initDaily();
  if (DATA.type === "post") {
    const items = DATA.quiz.map((q, i) => ({ id: `${DATA.id}:${i}`, ...q }));
    runQuiz($("#quiz"), items, { mode: "post" });
  }
  initSpeak();
  if (DATA.type === "think") initThink();
  if (DATA.type === "notes") renderNotes($("#notes-root"));
  if ($("#copy-notes")) renderCopyNotes($("#copy-notes"));
})();

/* ── 말해 보기 · 🔥 연속 기록 · 출근길 듣기 · 다시 꺼내기 (홈 폰 화면) ── */
(function () {
  "use strict";
  const DAY = Math.floor((Date.now() / 1000 + 9 * 3600) / 86400);
  const ymd = d => new Date(d * 864e5).toISOString().slice(0, 10);
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const MIC = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>';
  const PLAY = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M7 4.5v15l13-7.5z" fill="currentColor"/></svg>';
  const PAUSE = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" fill="currentColor"/></svg>';
  const X = t => String(t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const get = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) || d; } catch (e) { return d; } };
  const put = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };
  const ga = (n, p) => { if (window.gtag) gtag("event", n, p || {}); };

  // 🔥 연속 기록: 루틴을 끝낸 날 + 홈에서 한 문장이라도 말해 본 날
  function activeDays() {
    const set = new Set(get("ky_spoke", []));
    const s = get("ky_today_v1", {}), days = s.days || {};
    Object.keys(days).forEach(k => { const r = days[k]; if (r && r.l && r.s && r.r) set.add(Math.round(Date.parse(k) / 864e5)); });
    (s.stamps || []).forEach(k => set.add(Math.round(Date.parse(k) / 864e5)));
    return set;
  }
  function streak() {
    const a = activeDays(); let d = a.has(DAY) ? DAY : DAY - 1, n = 0;
    while (a.has(d)) { n++; d--; }
    return n;
  }
  function fire() {
    const room = document.querySelector(".room"); if (!room) return;
    let f = room.querySelector(".fire"); const n = streak();
    if (!n) { if (f) f.remove(); return; }
    if (!f) { f = document.createElement("span"); f.className = "fire"; room.insertBefore(f, room.querySelector(".badge")); }
    f.textContent = "🔥" + n; f.title = n + "일 연속 공부 중";
  }
  function spoke() {
    const a = get("ky_spoke", []); if (a.indexOf(DAY) < 0) { a.push(DAY); put("ky_spoke", a.slice(-60)); }
    fire(); document.dispatchEvent(new Event("ky-routine"));
  }
  document.addEventListener("ky-routine", () => setTimeout(fire, 0));
  fire();

  // 들린 말과 정답 비교: 단어가 얼마나 겹치나
  const words = t => String(t).toLowerCase().replace(/[’']/g, "").replace(/~/g, " ").replace(/[^a-z0-9 ]+/g, " ").split(/\s+/).filter(Boolean);
  function score(target, heard) {
    const t = words(target); if (!t.length) return 0;
    let best = 0;
    heard.forEach(h => { const hw = words(h); const hit = t.filter(w => hw.indexOf(w) > -1).length; best = Math.max(best, hit / t.length); });
    return best;
  }
  let rec = null;
  function listen(box, target, onDone) {
    if (rec) { try { rec.abort(); } catch (e) {} rec = null; }
    const r = new SR(); rec = r;
    r.lang = "en-US"; r.interimResults = false; r.maxAlternatives = 4;
    let got = false;
    box.classList.add("rec");
    r.onresult = e => { got = true; const alts = [].map.call(e.results[0], a => a.transcript); onDone(score(target, alts), alts[0] || ""); };
    r.onerror = e => { if (!got) onDone(-1, e.error || ""); got = true; };
    r.onend = () => { box.classList.remove("rec"); if (!got) onDone(-1, "no-speech"); rec = null; };
    try { r.start(); } catch (e) { box.classList.remove("rec"); onDone(-1, "start"); }
  }
  function sayBox(target, okMsg) {
    return '<div class="ks" data-t="' + X(target) + '">' + (SR
      ? '<div class="ks-row"><button type="button" class="ks-mic" aria-label="말하기 시작">' + MIC + '</button><span class="ks-t"><b>이제 직접 말해 보세요</b><small>마이크를 누르고 따라 말하면 바로 알려줘요</small></span></div>'
      : '<div class="ks-row"><span class="ks-t"><b>소리 내어 3번 따라 말해 보세요</b><small>이 브라우저에선 음성 확인이 안 돼요. 다 말했으면 오른쪽 버튼을 눌러요</small></span><button type="button" class="ks-done">다 말했어요</button></div>')
      + '</div>';
  }
  function result(box, s, heard, onOk) {
    const t = box.getAttribute("data-t"), row = box.querySelector(".ks-t");
    let h = box.querySelector(".ks-heard");
    if (s < 0) {
      const msg = heard === "not-allowed" || heard === "service-not-allowed" ? "마이크 사용을 허용해 주세요" : "잘 안 들렸어요. 한 번 더 눌러 말해 보세요";
      row.innerHTML = "<b>" + msg + "</b><small>조용한 곳에서 또박또박 말하면 더 잘 알아들어요</small>";
      if (h) h.remove(); return;
    }
    if (!h) { h = document.createElement("div"); h.className = "ks-heard"; box.appendChild(h); }
    h.innerHTML = "들린 말: <em>" + X(heard) + "</em>";
    box.classList.remove("ok", "near");
    if (s >= .75) { box.classList.add("ok"); row.innerHTML = "<b>정확해요! 오늘 한 문장 말했어요</b><small>다시 말하려면 마이크를 눌러요</small>"; onOk && onOk(); }
    else if (s >= .4) { box.classList.add("near"); row.innerHTML = "<b>거의 맞았어요!</b><small>정답: " + X(t) + " · 한 번 더 해 볼까요?</small>"; }
    else row.innerHTML = "<b>조금 달라요</b><small>정답: " + X(t) + " · 듣고 다시 말해 보세요</small>";
  }
  function fit() { if (window.KY_W && KY_W.fit) KY_W.fit(); }
  window.KY_SAY = { box: sayBox, listen: listen, result: result, spoke: spoke, sr: !!SR };

  // ① 퀴즈 카드: 정답을 들은 뒤 '말해 보기'
  const W = window.KY_W, tr = document.getElementById("mq-tr");
  if (tr && W) {
    [].forEach.call(tr.querySelectorAll(".mq"), c => {
      const en = (c.querySelector(".mq-en") || {}).textContent || "";
      const btn = c.querySelector(".mq-btn");
      if (btn && en) btn.insertAdjacentHTML("beforebegin", sayBox(en.trim()));
    });
    fit();
    tr.addEventListener("click", e => {
      const box = e.target.closest(".ks"); if (!box) return;
      const card = e.target.closest(".mq");
      const ok = () => { spoke(); ga("quiz_speak_ok", { days_ago: +(card && card.getAttribute("data-k")) || 0 }); };
      if (e.target.closest(".ks-done")) { box.classList.add("ok"); box.querySelector(".ks-t").innerHTML = "<b>잘했어요! 오늘 한 문장 말했어요</b><small>내일도 한 잔 하러 와요</small>"; ok(); fit(); return; }
      if (!e.target.closest(".ks-mic")) return;
      ga("quiz_speak_try");
      box.querySelector(".ks-t").innerHTML = '<b>듣고 있어요…</b><small>"' + X(box.getAttribute("data-t")) + '" 하고 말해 보세요</small>';
      listen(box, box.getAttribute("data-t"), (s, heard) => { result(box, s, heard, ok); fit(); });
    });
  }

  // 말해 본 문장을 내 공부방 기록에 담기
  function keep(it, src) {
    try {
      const s = JSON.parse(localStorage.getItem("ky_today_v1")) || {}, d = ymd(DAY);
      s.learned = s.learned || [];
      if (!s.learned.some(x => x.en === it.en && x.d === d)) s.learned.push({ en: it.en, ko: it.ko, a: it.a || it.au || "", d: d, src: src });
      localStorage.setItem("ky_today_v1", JSON.stringify(s));
    } catch (e) {}
  }
  const PLAY1 = '<svg class="mq-pl" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M7 4.5v15l13-7.5z" fill="currentColor"/></svg>';

  // ④ PC 홈: 오늘의 한 잔도 '맞혀 보기 → 정답 듣기 → 말해 보기'
  const hsTr = document.getElementById("hs-track");
  if (hsTr && W && W.L && W.L.length) {
    const at0 = k => W.L[((W.i0 - k) % W.L.length + W.L.length) % W.L.length];
    const pcAu = new Audio();
    [].forEach.call(hsTr.querySelectorAll(".hs-slide"), (sl, k) => {
      const T = at0(k), txt = sl.querySelector(".hs-txt"); if (!T || !txt) return;
      sl.classList.add("pq"); sl.setAttribute("data-k", k);
      const kick = txt.querySelector(".a-kicker");
      const box = '<div class="pq-box"><h2 class="pq-h">"' + X(T.ko) + '"<br>영어로 하면?</h2>' + (T.q ? '<span class="pq-q">' + X(T.q) + '</span>' : "")
        + '<div><button type="button" class="pq-me">' + PLAY1 + '눌러서 정답 듣기</button></div><p class="pq-hint">정답을 들으면 직접 말해 볼 수 있어요</p></div>';
      if (kick) kick.insertAdjacentHTML("afterend", box); else txt.insertAdjacentHTML("afterbegin", box);
      const btns = txt.querySelector(".hs-btns");
      if (btns) btns.insertAdjacentHTML("beforebegin", sayBox(T.en));
      sl.setAttribute("data-a", T.au || "");
    });
    hsTr.addEventListener("click", e => {
      const sl = e.target.closest(".hs-slide"); if (!sl) return;
      const say = () => { const a = sl.getAttribute("data-a"); if (!a) return; try { if (pcAu.src.indexOf(a) < 0) pcAu.src = a; pcAu.currentTime = 0; pcAu.play().catch(() => {}); } catch (x) {} };
      if (e.target.closest(".pq-me")) { sl.classList.remove("pq"); say(); ga("quiz_reveal", { days_ago: +sl.getAttribute("data-k"), from: "pc" }); return; }
      const box = e.target.closest(".ks"); if (!box) return;
      const T = at0(+sl.getAttribute("data-k"));
      const ok = () => { spoke(); keep(T, "daily"); ga("quiz_speak_ok", { days_ago: +sl.getAttribute("data-k"), from: "pc" }); };
      if (e.target.closest(".ks-done")) { box.classList.add("ok"); box.querySelector(".ks-t").innerHTML = "<b>잘했어요! 오늘 한 문장 말했어요</b><small>내일도 한 잔 하러 와요</small>"; ok(); return; }
      if (!e.target.closest(".ks-mic")) return;
      ga("quiz_speak_try", { from: "pc" });
      box.querySelector(".ks-t").innerHTML = '<b>듣고 있어요…</b><small>"' + X(box.getAttribute("data-t")) + '" 하고 말해 보세요</small>';
      listen(box, box.getAttribute("data-t"), (s, heard) => result(box, s, heard, ok));
    });
  }

  // ⑤ 글 끝 '입으로 마무리하기'
  const ps = document.getElementById("say-end");
  if (ps) {
    let L5 = []; try { L5 = JSON.parse(ps.querySelector(".ps-data").textContent); } catch (e) {}
    const body = ps.querySelector(".ps-body"), au5 = new Audio(); let i5 = 0;
    const draw = () => {
      const it = L5[i5];
      body.innerHTML = '<div class="ps-card"><p class="ps-ko">"' + X(it.ko) + '"</p><p class="ps-sub">한국어만 보고 영어로 말해 보세요 · ' + (i5 + 1) + " / " + L5.length + "</p>"
        + sayBox(it.en).replace('<div class="ks"', '<div class="ks ps-ks"') + '<div class="ps-ans" hidden><b>' + X(it.en) + '</b><button type="button" class="ps-play" aria-label="원어민 발음">' + PLAY1 + '</button></div>'
        + '<div class="ps-nav"><button type="button" class="ps-show">정답 보기</button>' + (i5 < L5.length - 1 ? '<button type="button" class="ps-next">다음 문장 ›</button>' : "") + "</div></div>"
        + '<div class="ps-dots">' + L5.map((_, j) => "<i" + (j === i5 ? ' class="on"' : "") + "></i>").join("") + "</div>";
    };
    const reveal = () => { const a = body.querySelector(".ps-ans"); if (a) a.hidden = false; const sh = body.querySelector(".ps-show"); if (sh) sh.hidden = true; };
    const hear = () => { const a = L5[i5].a; if (!a) return; try { au5.src = a; au5.play().catch(() => {}); } catch (e) {} };
    if (L5.length) draw();
    ps.addEventListener("click", e => {
      if (e.target.closest(".ps-show")) { reveal(); hear(); return; }
      if (e.target.closest(".ps-play")) { hear(); return; }
      if (e.target.closest(".ps-next")) { i5 = Math.min(L5.length - 1, i5 + 1); draw(); return; }
      const box = e.target.closest(".ks"); if (!box) return;
      const it = L5[i5], ok = () => { spoke(); keep(it, "post"); reveal(); ga("post_speak_ok", { n: i5 + 1 }); };
      if (e.target.closest(".ks-done")) { box.classList.add("ok"); box.querySelector(".ks-t").innerHTML = "<b>잘했어요!</b><small>내 공부방 '말해 본 문장'에 담았어요</small>"; ok(); return; }
      if (!e.target.closest(".ks-mic")) return;
      ga("post_speak_try");
      box.querySelector(".ks-t").innerHTML = "<b>듣고 있어요…</b><small>기억나는 대로 영어로 말해 보세요</small>";
      listen(box, it.en, (sc, heard) => { result(box, sc, heard, ok); if (sc >= .75) { const t = box.querySelector(".ks-t small"); if (t) t.textContent = "내 공부방 '말해 본 문장'에 담았어요"; } });
    });
  }

  // ②③ 출근길 듣기 · 다시 꺼내기 (폰 홈, 상황별 고르기 위)
  const home = document.querySelector(".m-home"), gp = document.getElementById("gp") || (home && home.querySelector(".gp-me"));
  if (!home || !W || !W.L || !W.L.length) return;
  const L = W.L, at = k => L[((W.i0 - k) % L.length + L.length) % L.length];
  const week = Array.from({ length: Math.min(7, L.length) }, (_, k) => at(k)).filter(x => x.au);
  const old = at(3);
  const wrap = document.createElement("div"); wrap.className = "kx";
  wrap.innerHTML =
    '<section class="kx-card kx-cm"><div class="kx-row"><button type="button" class="kx-play" aria-label="출근길 듣기 재생">' + PLAY + '</button>'
    + '<span class="kx-t"><b>출근길 듣기 · 약 3분</b><small class="kx-now">이번 주 ' + week.length + '문장을 두 번씩 이어서 들려줘요</small></span></div>'
    + '<div class="kx-chips">' + week.map((x, i) => '<span data-i="' + i + '">' + X(x.ko) + '</span>').join("") + '</div>'
    + (old ? '<div class="kx-rv"><button type="button" class="kx-rvt" aria-expanded="false"><span>복습 · <b>"' + X(old.ko) + '"</b> 기억나요?</span><i>›</i></button>'
      + '<div class="kx-rvb" hidden>' + sayBox(old.en) + '<button type="button" class="kx-show">정답 보기</button><p class="kx-ans" hidden><b>' + X(old.en) + '</b></p></div></div>' : "")
    + '</section>';
  // 출근길 카드는 '오늘의 한 잔' 바로 아래에 (복습은 카드 안 한 줄, 누르면 펼침)
  const mqs = document.getElementById("mqs");
  if (mqs && mqs.parentNode === home) home.insertBefore(wrap, mqs.nextSibling); else (gp || home.firstChild).parentNode.insertBefore(wrap, gp || null);

  // 출근길 듣기 재생기
  const cm = wrap.querySelector(".kx-cm"), pb = cm.querySelector(".kx-play"), now = cm.querySelector(".kx-now");
  const au = new Audio(); let idx = 0, rep = 0, on = false, timer = null;
  const chips = cm.querySelectorAll(".kx-chips span");
  function mark() { [].forEach.call(chips, (c, i) => c.className = on && i === idx ? "on" : ""); const c = chips[idx]; if (on && c) c.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" }); }
  function step() {
    if (!on) return;
    if (idx >= week.length) { stop(); now.textContent = "다 들었어요! 내일 또 들어요"; ga("commute_done"); return; }
    const x = week[idx]; now.textContent = (idx + 1) + "/" + week.length + " · " + x.ko; mark();
    au.src = x.au; au.play().catch(stop);
  }
  au.onended = () => { if (!on) return; rep++; if (rep < 2) timer = setTimeout(() => { au.currentTime = 0; au.play().catch(stop); }, 1500); else { rep = 0; idx++; timer = setTimeout(step, 2200); } };
  function stop() { on = false; clearTimeout(timer); au.pause(); pb.innerHTML = PLAY; pb.setAttribute("aria-label", "출근길 듣기 재생"); mark(); }
  pb.addEventListener("click", () => {
    if (on) { stop(); return; }
    if (idx >= week.length) idx = 0;
    on = true; rep = 0; pb.innerHTML = PAUSE; pb.setAttribute("aria-label", "일시정지"); ga("commute_play"); step();
  });
  cm.querySelector(".kx-chips").addEventListener("click", e => { const c = e.target.closest("span"); if (!c) return; idx = +c.getAttribute("data-i"); rep = 0; clearTimeout(timer); if (!on) { on = true; pb.innerHTML = PAUSE; } step(); });

  // 다시 꺼내기
  const rv = wrap.querySelector(".kx-rv");
  if (rv) rv.addEventListener("click", e => {
    const ans = rv.querySelector(".kx-ans");
    const tg = e.target.closest(".kx-rvt");
    if (tg) { const b = rv.querySelector(".kx-rvb"); b.hidden = !b.hidden; tg.setAttribute("aria-expanded", String(!b.hidden)); rv.classList.toggle("open", !b.hidden); return; }
    if (e.target.closest(".kx-show")) { ans.hidden = false; e.target.closest(".kx-show").hidden = true; if (old.au) { au.src = old.au; au.play().catch(() => {}); } return; }
    const box = e.target.closest(".ks"); if (!box) return;
    const ok = () => { spoke(); ans.hidden = false; rv.querySelector(".kx-show").hidden = true; ga("review_speak_ok"); };
    if (e.target.closest(".ks-done")) { box.classList.add("ok"); box.querySelector(".ks-t").innerHTML = "<b>잘했어요!</b><small>정답을 확인해 보세요</small>"; ok(); return; }
    if (!e.target.closest(".ks-mic")) return;
    box.querySelector(".ks-t").innerHTML = "<b>듣고 있어요…</b><small>기억나는 대로 영어로 말해 보세요</small>";
    listen(box, old.en, (s, heard) => result(box, s, heard, ok));
  });
})();

/* 서비스워커: 페이지를 늘 새로 확인(no-cache), 글꼴·음성은 저장 */
if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));

/* ── 기록 백업 (내 공부방) · 기록 오래 보관 요청 ── */
(function () {
  try { if (navigator.storage && navigator.storage.persist && !/Firefox/i.test(navigator.userAgent)) navigator.storage.persisted().then(p => { if (!p) navigator.storage.persist(); }); } catch (e) {}
  const out = document.querySelector(".js-bk-out"), inp = document.querySelector(".js-bk-in"), file = document.querySelector(".js-bk-file");
  if (!out || !inp || !file) return;
  const SKIP = /^(appPreview)$/;
  function toast(t) { let el = document.getElementById("bk-toast"); if (!el) { el = document.createElement("div"); el.id = "bk-toast"; el.className = "bk-toast"; document.body.appendChild(el); } el.textContent = t; el.classList.add("on"); clearTimeout(el._t); el._t = setTimeout(() => el.classList.remove("on"), 2600); }
  function dump() { const d = {}; for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (!SKIP.test(k)) d[k] = localStorage.getItem(k); } return d; }
  out.addEventListener("click", async () => {
    const d = dump(); if (!Object.keys(d).length) { toast("아직 저장된 기록이 없어요"); return; }
    const day = new Date(), ymd = day.getFullYear() + String(day.getMonth() + 1).padStart(2, "0") + String(day.getDate()).padStart(2, "0");
    const name = "cafeinenglish-backup-" + ymd + ".json";
    const blob = new Blob([JSON.stringify({ app: "cafeinenglish", v: 1, at: day.toISOString(), data: d })], { type: "application/json" });
    try {
      const f = new File([blob], name, { type: "application/json" });
      if (navigator.canShare && navigator.canShare({ files: [f] })) { await navigator.share({ files: [f], title: "카페인영어 기록 백업" }); return; }
    } catch (e) { if (e && e.name === "AbortError") return; }
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    toast("기록 파일을 저장했어요");
  });
  inp.addEventListener("click", () => file.click());
  // 합치기: 배열은 없는 것만 더하고, 객체는 키별로 합치고, 숫자는 큰 값, 그 밖엔 지금 기록 유지
  let added = 0;
  function merge(a, b) {
    if (Array.isArray(a) && Array.isArray(b)) { const seen = new Set(a.map(x => JSON.stringify(x))); b.forEach(x => { const s = JSON.stringify(x); if (!seen.has(s)) { a.push(x); seen.add(s); added++; } }); return a; }
    if (a && b && typeof a === "object" && typeof b === "object") { Object.keys(b).forEach(k => { if (!(k in a)) { a[k] = b[k]; added++; } else a[k] = merge(a[k], b[k]); }); return a; }
    if (typeof a === "number" && typeof b === "number") return Math.max(a, b);
    return a;
  }
  file.addEventListener("change", () => {
    const f = file.files && file.files[0]; if (!f) return;
    const r = new FileReader();
    r.onload = () => {
      let j; try { j = JSON.parse(r.result); } catch (e) { toast("카페인영어 기록 파일이 아니에요"); return; }
      if (!j || j.app !== "cafeinenglish" || !j.data) { toast("카페인영어 기록 파일이 아니에요"); return; }
      added = 0;
      Object.keys(j.data).forEach(k => {
        if (SKIP.test(k)) return;
        const nv = j.data[k], cur = localStorage.getItem(k);
        if (cur === null) { localStorage.setItem(k, nv); added++; return; }
        let A, B; try { A = JSON.parse(cur); B = JSON.parse(nv); } catch (e) { return; }
        localStorage.setItem(k, JSON.stringify(merge(A, B)));
      });
      file.value = "";
      toast(added ? "기록을 가져왔어요 · " + added + "개 추가" : "이미 같은 기록이 있어요");
      if (added) setTimeout(() => location.reload(), 1200);
    };
    r.readAsText(f);
  });
})();
