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
      document.documentElement.classList.toggle("v-floating", on && innerWidth < 1024);
    }
    const io = new IntersectionObserver(([en]) => {
      past = !en.isIntersecting && en.boundingClientRect.top < 0;
      if (en.isIntersecting) dismissed = false;
      updateFloat();
    }, { rootMargin: `-${Math.round(headerH())}px 0px 0px 0px` });
    io.observe(slot);
    $(".v-close").onclick = () => { dismissed = true; updateFloat(); };
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
