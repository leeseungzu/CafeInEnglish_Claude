/* 카페인영어 영어 도구 (/tools/) — 영문 이름 변환기 · 영문 주소 변환기
   데이터는 페이지의 <script id="page-data"> 에 들어 있어요 (build.py 가 넣어요). */
(function () {
  "use strict";
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const DATA = (() => { try { return JSON.parse($("#page-data").textContent); } catch (e) { return {}; } })();
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ga = (n, p) => { try { window.gtag && gtag("event", n, p || {}); } catch (e) {} };

  /* ---------- 복사 ---------- */
  function toast(msg) {
    let t = $(".tl-toast");
    if (!t) { t = document.createElement("div"); t.className = "tl-toast"; t.setAttribute("role", "status"); document.body.appendChild(t); }
    t.textContent = msg; t.classList.add("show");
    clearTimeout(toast.h); toast.h = setTimeout(() => t.classList.remove("show"), 1600);
  }
  function copyText(text, btn) {
    const done = () => {
      toast("복사했어요");
      if (btn) { btn.classList.add("ok"); const o = btn.dataset.l || btn.textContent; btn.dataset.l = o; btn.textContent = "복사됨"; setTimeout(() => { btn.textContent = o; btn.classList.remove("ok"); }, 1300); }
    };
    const fallback = () => {
      const ta = document.createElement("textarea"); ta.value = text; ta.setAttribute("readonly", ""); ta.style.cssText = "position:fixed;top:-99px;opacity:0";
      document.body.appendChild(ta); ta.select(); try { document.execCommand("copy"); done(); } catch (e) { toast("길게 눌러 복사해 주세요"); } ta.remove();
    };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback); else fallback();
  }
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-copy]");
    if (b) { copyText(b.dataset.copy, b); ga("tool_copy", { tool: DATA.tool || "", field: b.dataset.f || "" }); }
  });

  /* ---------- 결과 공유 (카톡·인스타·링크) ---------- */
  let SHARE = null;
  const QS = new URLSearchParams(location.search);
  function setShare(text, q) { SHARE = { text, q }; $$(".tl-share-row").forEach(r => { r.hidden = false; }); }
  document.addEventListener("click", e => {
    const b = e.target.closest(".tl-share-row .tl-share"); if (!b || !SHARE) return;
    const url = location.origin + location.pathname + (SHARE.q ? "?" + SHARE.q : "");
    ga("tool_share", { tool: DATA.tool || "" });
    if (navigator.share) navigator.share({ title: document.title.split(" | ")[0], text: SHARE.text, url }).catch(() => {});
    else copyText(SHARE.text + "\n" + url, b);
  });
  const SHARE_ROW = '<div class="tl-share-row"><button type="button" class="tl-share">결과 공유하기</button></div>';

  /* =========================================================
     1. 한글 이름 → 영문 (국어의 로마자 표기법, 인명은 음운 변화 미반영)
     ========================================================= */
  const CHO = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"];
  const JUNG = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"];
  const JONG = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p", "t", "t", "ng", "t", "t", "k", "t", "p", "t"];
  const isHan = ch => { const c = ch.charCodeAt(0); return c >= 0xAC00 && c <= 0xD7A3; };
  const parts = ch => { const c = ch.charCodeAt(0) - 0xAC00; return [Math.floor(c / 588), Math.floor((c % 588) / 28), c % 28]; };
  const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;
  // 한 음절 표기. prevL: 앞 음절 받침이 ㄹ이면 ㄹㄹ → ll
  function rrSyl(ch, prevL) {
    const [c, v, f] = parts(ch);
    return (c === 5 && prevL ? "l" : CHO[c]) + JUNG[v] + JONG[f];
  }
  function rrWord(word) {
    let out = "", prevL = false;
    for (const ch of word) { out += rrSyl(ch, prevL); prevL = parts(ch)[2] === 8; }
    return out;
  }
  // 이름 음절에서 자주 보이는 다른 표기 (첫 번째는 로마자 표기법 그대로)
  const ALT = {
    "영": ["Young"], "이": ["Yi", "Lee"], "의": ["Eui"], "희": ["Hee"], "우": ["Woo"], "운": ["Woon"], "욱": ["Wook"], "웅": ["Woong"],
    "오": ["Oh"], "아": ["Ah"], "안": ["Ahn"], "어": ["Uh"], "여": ["Yuh"], "연": ["Yun"], "열": ["Yul"], "엽": ["Yup"], "억": ["Uk"], "언": ["Un"],
    "지": ["Jee"], "리": ["Lee"], "린": ["Lin"], "시": ["Shi"], "신": ["Shin"], "식": ["Shik"], "실": ["Shil"], "심": ["Shim"], "섭": ["Sup"],
    "선": ["Sun"], "설": ["Sul"], "성": ["Sung"], "서": ["Suh"], "석": ["Suk"], "정": ["Jung"], "준": ["Joon"], "주": ["Joo"], "수": ["Soo"],
    "숙": ["Sook"], "순": ["Soon"], "훈": ["Hoon"], "후": ["Hoo"], "현": ["Hyun"], "형": ["Hyung"], "혁": ["Hyuk"], "경": ["Kyung"], "규": ["Kyu"],
    "기": ["Ki"], "근": ["Keun"], "금": ["Keum"], "광": ["Kwang"], "건": ["Gun", "Kun"], "권": ["Kwon"], "국": ["Kook"], "길": ["Kil"], "강": ["Kang"],
    "구": ["Koo"], "고": ["Ko"], "겸": ["Kyum"], "결": ["Kyul"], "균": ["Kyun"], "명": ["Myung"], "병": ["Byung"], "평": ["Pyung"], "철": ["Chul"],
    "천": ["Chun"], "청": ["Chung"], "범": ["Bum"], "별": ["Byul"], "덕": ["Duk"], "두": ["Doo"], "부": ["Boo"], "무": ["Moo"], "문": ["Moon"],
    "윤": ["Yoon"], "유": ["Yoo"], "전": ["Jun"], "조": ["Cho"], "추": ["Choo"], "헌": ["Hun"], "백": ["Baik"], "래": ["Lae"], "란": ["Lan"],
    "라": ["La"], "루": ["Roo"], "용": [], "중": [], "은": [], "진": [], "민": [], "승": [], "재": [], "태": [], "혜": [], "예": []
  };
  const SUR = {}; (DATA.surnames || []).forEach(r => { SUR[r[0]] = r[1]; });
  const COMPOUND = DATA.compound || [];

  function sylOptions(ch, prevL) {
    const rr = cap(rrSyl(ch, prevL));
    const extra = (ALT[ch] || []).filter(x => x !== rr);
    // 사전에 없는 음절: u로 끝나면 oo 표기를 함께 보여줘요 (예: 누 Nu → Noo)
    if (!ALT[ch] && /[^aeiouy]u$/i.test(rr)) extra.push(rr.slice(0, -1) + "oo");
    return [rr].concat(extra);
  }

  function initName() {
    const form = $("#nm-form"); if (!form) return;
    const inp = $("#nm-in"), out = $("#nm-out"), two = $("#nm-two");
    let state = null, last = "", manual = null;

    function analyze(raw) {
      const s = (raw || "").replace(/\s+/g, "");
      if (!s) return { err: "이름을 한글로 입력해 주세요." };
      if (![...s].every(isHan)) return { err: "한글 이름만 입력할 수 있어요. 예) 홍길동" };
      if (s.length < 2 || s.length > 6) return { err: "성과 이름을 합쳐 2~6글자로 입력해 주세요." };
      // 두 글자 성: 사용자가 직접 켜거나 끈 값이 있으면 그대로, 없으면 남궁·황보 등을 자동으로
      let sl = 1;
      if (manual !== null) sl = manual ? 2 : 1;
      else if (s.length >= 3 && COMPOUND.indexOf(s.slice(0, 2)) > -1) sl = 2;
      two.checked = sl === 2;
      if (s.length - sl < 1) return { err: "이름 글자가 없어요. 성이 두 글자라면 이름까지 함께 입력해 주세요." };
      const sur = s.slice(0, sl), giv = s.slice(sl);
      const surRR = cap(rrWord(sur));
      const surOpts = [...new Set((SUR[sur] || []).concat([surRR]))];
      const syl = []; let prevL = false;
      for (const ch of giv) { syl.push({ ch, opts: sylOptions(ch, prevL), i: 0 }); prevL = parts(ch)[2] === 8; }
      return { sur, giv, surRR, surOpts, si: 0, syl };
    }

    function joined(st, hy) {
      const ps = st.syl.map(x => x.opts[x.i].toLowerCase());
      return cap(ps.join(hy ? "-" : ""));
    }

    function row(label, val, f, sub) {
      return `<div class="tl-row"><span class="tl-k">${esc(label)}${sub ? `<small>${esc(sub)}</small>` : ""}</span>` +
        `<b class="tl-v">${esc(val)}</b><button type="button" class="tl-cp" data-copy="${esc(val)}" data-f="${esc(f)}">복사</button></div>`;
    }

    function render() {
      const st = state;
      if (st.err) { out.innerHTML = `<p class="tl-err">${esc(st.err)}</p>`; out.hidden = false; return; }
      const S = st.surOpts[st.si], G = joined(st), GH = joined(st, true);
      const isStd = st.syl.every(x => x.i === 0);
      const altAll = st.syl.some(x => x.opts.length > 1);
      out.innerHTML =
        `<div class="tl-hero-res"><span class="tl-tag">${isStd && S === (SUR[st.sur] || [st.surRR])[0] ? "추천 표기" : "선택한 표기"}</span>` +
        `<p class="tl-big"><span>${esc(S)} ${esc(G)}</span></p>` +
        `<p class="tl-big-sub">${esc(st.sur + st.giv)} · 이름 ${esc(G)} · 성 ${esc(S)}</p></div>` +
        `<div class="tl-pick"><p class="tl-pick-h">글자를 누르면 다른 표기로 바뀌어요</p><div class="tl-syls">` +
        `<button type="button" class="tl-syl sur${st.surOpts.length > 1 ? " more" : ""}" data-s="sur"><small>${esc(st.sur)} · 성</small><b>${esc(S)}</b>${dots(st.surOpts.length, st.si)}</button>` +
        st.syl.map((x, k) => `<button type="button" class="tl-syl${x.opts.length > 1 ? " more" : ""}" data-s="${k}"><small>${esc(x.ch)}</small><b>${esc(x.opts[x.i])}</b>${dots(x.opts.length, x.i)}</button>`).join("") +
        `</div>${altAll || st.surOpts.length > 1 ? `<p class="tl-pick-n"><span class="tl-dot on"></span> 표시가 있는 글자는 다른 표기도 있어요. 첫 번째가 로마자 표기법 기준이에요.</p>` : ""}</div>` +
        `<div class="tl-rows">` +
        row("여권 형식", `${S.toUpperCase()} ${G.toUpperCase()}`, "passport", "성 · 이름 순, 대문자") +
        row("성 (Surname)", S.toUpperCase(), "surname") +
        row("이름 (Given name)", G.toUpperCase(), "given") +
        row("해외 사이트·이메일", `${G} ${S}`, "western", "이름 먼저") +
        row("붙임표 넣은 이름", `${GH} ${S}`, "hyphen", "음절 구분이 필요할 때") +
        `</div>` + SHARE_ROW;
      out.hidden = false;
      setShare(`${st.sur + st.giv} 영문 이름: ${S} ${G}`, "name=" + encodeURIComponent(st.sur + st.giv));
    }
    const dots = (n, i) => n > 1 ? `<span class="tl-dots">${Array.from({ length: n }, (_, k) => `<i${k === i ? ' class="on"' : ""}></i>`).join("")}</span>` : "";

    out.addEventListener("click", e => {
      const b = e.target.closest(".tl-syl"); if (!b || !state || state.err) return;
      if (b.dataset.s === "sur") state.si = (state.si + 1) % state.surOpts.length;
      else { const x = state.syl[+b.dataset.s]; x.i = (x.i + 1) % x.opts.length; }
      render(); const nb = $(`.tl-syl[data-s="${b.dataset.s}"]`, out); nb && nb.focus();
    });
    form.addEventListener("submit", e => {
      e.preventDefault();
      if (inp.value.trim() !== last) manual = null; // 새 이름이면 두 글자 성 여부를 다시 자동으로 판단
      last = inp.value.trim(); state = analyze(inp.value); render();
      if (!state.err) { ga("tool_use", { tool: "english_name" }); try { history.replaceState(null, "", "?name=" + encodeURIComponent(inp.value.trim())); } catch (er) {} }
    });
    two.addEventListener("change", () => { manual = two.checked; if (inp.value.trim()) { last = inp.value.trim(); state = analyze(inp.value); render(); } });
    // 예시 버튼
    $$("[data-ex]").forEach(b => b.addEventListener("click", () => { inp.value = b.dataset.ex; form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event("submit")); }));
    const q = new URLSearchParams(location.search).get("name");
    if (q) { inp.value = q; last = q.trim(); state = analyze(q); render(); }
  }

  /* =========================================================
     2. 영문 주소 (행정안전부 도로명주소 영문 검색 API, JSONP)
     ========================================================= */
  const METRO = ["Seoul", "Busan", "Daegu", "Incheon", "Gwangju", "Daejeon", "Ulsan", "Sejong-si"];
  function jsonp(url) {
    return new Promise((res, rej) => {
      const cb = "__ky" + Date.now() + Math.floor(Math.random() * 1e5), s = document.createElement("script");
      const t = setTimeout(() => { clean(); rej(new Error("timeout")); }, 9000);
      function clean() { clearTimeout(t); try { delete window[cb]; } catch (e) { window[cb] = undefined; } s.remove(); }
      window[cb] = d => { clean(); res(d); };
      s.onerror = () => { clean(); rej(new Error("network")); };
      s.src = url + "&callback=" + cb; document.head.appendChild(s);
    });
  }
  // 검색어 정리: API가 막는 특수문자·SQL 예약어 제거, 동·호수·층은 따로 뽑기
  function splitKeyword(raw) {
    let k = (raw || "").replace(/[%=><\[\]]/g, " ");
    const d = {};
    let m = k.match(/(\d+)\s*동\s*(\d+)\s*호/);
    if (m) { d.dong = m[1]; d.ho = m[2]; k = k.replace(m[0], " "); }
    else {
      m = k.match(/(\d+)\s*-\s*(\d+)\s*호?\s*$/); // 101-1004
      if (m && /(로|길)\s*\d+/.test(k.replace(m[0], ""))) { d.dong = m[1]; d.ho = m[2]; k = k.replace(m[0], " "); }
      m = k.match(/(\d+)\s*호/); if (m) { d.ho = m[1]; k = k.replace(m[0], " "); }
      m = k.match(/(\d+)\s*동(?![가-힣])/); if (m) { d.dong = m[1]; k = k.replace(m[0], " "); }
    }
    m = k.match(/(지하\s*)?(\d+)\s*층/); if (m) { d.floor = (m[1] ? "B" : "") + m[2]; k = k.replace(m[0], " "); }
    k = k.replace(/\b(OR|SELECT|INSERT|DELETE|UPDATE|CREATE|DROP|EXEC|UNION|FETCH|DECLARE|TRUNCATE)\b/gi, " ");
    k = k.replace(/[,()]/g, " ").replace(/\s+/g, " ").trim();
    return { k, d };
  }
  function split(j) {
    const si = j.siNm || "", sgg = (j.sggNm || "").trim();
    let parts = (j.roadAddr || "").split(",").map(x => x.trim()).filter(Boolean);
    if (parts.length && parts[parts.length - 1] === si) parts.pop();
    let city = si, line1;
    if (METRO.indexOf(si) > -1 || !sgg) {
      line1 = parts.join(", ");
      if (si === "Sejong-si") city = "Sejong";
    } else {
      const toks = sgg.split(/[\s,]+/).filter(Boolean);
      city = toks.find(t => /-si$/.test(t)) || toks.find(t => /-gun$/.test(t)) || toks[0];
      parts = parts.filter(p => p !== city);
      if (parts.length && parts[parts.length - 1] === sgg) { parts.pop(); toks.filter(t => t !== city).forEach(t => parts.push(t)); }
      line1 = parts.join(", ");
    }
    return { line1, city, state: si === "Sejong-si" ? "Sejong" : si, zip: j.zipNo || "" };
  }
  function detailText(d, style) {
    const dong = (d.dong || "").trim(), ho = (d.ho || "").trim(), f0 = (d.floor || "").trim().replace(/^b/i, "B"), fl = f0 ? (/^B/.test(f0) ? f0 : f0 + "F") : "";
    if (style === "short") {
      if (dong && ho) return `#${dong}-${ho}`;
      if (ho) return `#${ho}`;
      return fl;
    }
    const a = [];
    if (dong) a.push(`${dong}-dong`);
    if (fl && !ho) a.push(fl);
    if (ho) a.push(`${ho}-ho`);
    return a.join(" ");
  }

  function initAddr() {
    const form = $("#ad-form"); if (!form) return;
    const inp = $("#ad-in"), list = $("#ad-list"), out = $("#ad-out");
    const key = /[?&]test=1/.test(location.search) ? "TESTJUSOGOKR" : (DATA.jusoKey || "");
    let page = 1, kw = "", det = {}, items = [], pick = null, style = "long";

    if (!key) { form.querySelector("button").disabled = true; list.innerHTML = '<p class="tl-err">주소 검색을 준비하고 있어요. 조금만 기다려 주세요.</p>'; list.hidden = false; return; }

    async function search(more) {
      if (!more) { page = 1; items = []; }
      list.hidden = false;
      if (!more) list.innerHTML = '<p class="tl-wait">찾는 중이에요…</p>';
      const url = "https://business.juso.go.kr/addrlink/addrEngApiJsonp.do?confmKey=" + encodeURIComponent(key) +
        "&currentPage=" + page + "&countPerPage=10&resultType=json&keyword=" + encodeURIComponent(kw);
      try {
        const r = await jsonp(url), res = r && r.results, c = res && res.common;
        if (!c) throw new Error("bad");
        if (c.errorCode !== "0") { list.innerHTML = `<p class="tl-err">${esc(errMsg(c.errorCode, c.errorMessage))}</p>`; return; }
        items = items.concat(res.juso || []);
        const total = +c.totalCount || 0;
        if (!items.length) { list.innerHTML = '<p class="tl-err">검색 결과가 없어요. 도로명과 건물번호(예: 테헤란로 152)나 건물 이름으로 찾아 보세요.</p>'; return; }
        list.innerHTML = `<p class="tl-cnt">검색 결과 <b>${total.toLocaleString()}</b>건 · 내 주소를 눌러 주세요</p>` +
          items.map((j, i) => `<button type="button" class="tl-addr" data-i="${i}"><b>${esc(j.roadAddr)}</b><span>${esc(j.korAddr)}</span><em>${esc(j.zipNo)}</em></button>`).join("") +
          (items.length < total ? '<button type="button" class="tl-more" id="ad-more">결과 더 보기</button>' : "");
        ga("tool_use", { tool: "english_address" });
      } catch (e) {
        list.innerHTML = '<p class="tl-err">주소 서버에 연결하지 못했어요. 잠시 뒤 다시 검색해 주세요.</p>';
      }
    }
    function errMsg(code, msg) {
      return ({ E0005: "검색어를 입력해 주세요.", E0006: "시·도 이름만으로는 찾을 수 없어요. 도로명이나 건물 이름을 같이 입력해 주세요.", E0008: "한 글자로는 찾을 수 없어요.", E0009: "숫자만으로는 찾을 수 없어요.", E0010: "검색어가 너무 길어요.", E0015: "결과가 너무 많아요. 도로명과 건물번호까지 입력해 주세요." })[code] || ("주소 검색 오류: " + msg);
    }
    function renderOut() {
      if (!pick) return;
      const p = split(pick), l2 = detailText(det, style);
      const one = [l2, p.line1, p.city === p.state ? p.city : `${p.city}, ${p.state}`].filter(Boolean).join(", ") + ` ${p.zip}, Republic of Korea`;
      const r = (k, v, f, sub) => v ? `<div class="tl-row"><span class="tl-k">${esc(k)}${sub ? `<small>${esc(sub)}</small>` : ""}</span><b class="tl-v">${esc(v)}</b><button type="button" class="tl-cp" data-copy="${esc(v)}" data-f="${f}">복사</button></div>` : "";
      $("#ad-res").innerHTML =
        `<div class="tl-hero-res"><span class="tl-tag">영문 주소</span><p class="tl-addr-big">${esc(one)}</p>` +
        `<button type="button" class="tl-cp wide" data-copy="${esc(one)}" data-f="full">한 줄 주소 복사</button></div>` +
        `<p class="tl-sec">해외 쇼핑몰 칸별로 넣기</p><div class="tl-rows">` +
        r("Address Line 1", p.line1, "line1", "도로명 주소") +
        (l2 ? r("Address Line 2", l2, "line2", "동·호수") : `<div class="tl-row empty"><span class="tl-k">Address Line 2<small>동·호수</small></span><b class="tl-v">위에서 동·호수를 넣으면 채워져요</b></div>`) +
        r("City", p.city, "city", "시·군") + r("State / Province", p.state, "state", "시·도") +
        r("ZIP / Postal Code", p.zip, "zip", "우편번호") + r("Country", "Republic of Korea", "country", "South Korea로 골라도 돼요") +
        `</div><p class="tl-src">한글 주소 · ${esc(pick.korAddr)}</p>`;
    }

    list.addEventListener("click", e => {
      if (e.target.id === "ad-more") { page++; search(true); return; }
      const b = e.target.closest(".tl-addr"); if (!b) return;
      pick = items[+b.dataset.i];
      $$(".tl-addr", list).forEach(x => x.classList.toggle("on", x === b));
      out.hidden = false;
      ["dong", "ho", "floor"].forEach(k => { $("#ad-" + k).value = det[k] || ""; });
      renderOut();
      setTimeout(() => out.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    });
    ["dong", "ho", "floor"].forEach(k => $("#ad-" + k).addEventListener("input", e => { det[k] = e.target.value.replace(/[^0-9a-zA-Z]/g, ""); e.target.value = det[k]; renderOut(); }));
    $$("#ad-style button").forEach(b => b.addEventListener("click", () => { style = b.dataset.v; $$("#ad-style button").forEach(x => x.classList.toggle("on", x === b)); renderOut(); }));
    form.addEventListener("submit", e => {
      e.preventDefault();
      const s = splitKeyword(inp.value);
      if (s.k.length < 2) { list.hidden = false; list.innerHTML = '<p class="tl-err">도로명주소나 건물 이름을 입력해 주세요. 예) 테헤란로 152</p>'; return; }
      kw = s.k; det = s.d; pick = null; out.hidden = true; search(false);
    });
    $$("[data-ex]").forEach(b => b.addEventListener("click", () => { inp.value = b.dataset.ex; form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event("submit")); }));
  }

  initName();
  initAddr();

  /* =========================================================
     3. 점수 도구 — 토익 계산기 · 오픽 자가 진단 · 토익스피킹 등급 · 시험 비교 사다리
     ========================================================= */
  // 슬라이더 + 숫자 칸을 서로 맞춰 주는 도우미
  function pair(rangeId, numId, onChange) {
    const r = $("#" + rangeId), n = $("#" + numId); if (!r || !n) return null;
    const clamp = v => Math.max(+r.min, Math.min(+r.max, Math.round((+v || 0) / (+r.step || 1)) * (+r.step || 1)));
    r.addEventListener("input", () => { n.value = r.value; onChange(); });
    n.addEventListener("input", () => { if (n.value === "") return; r.value = clamp(n.value); onChange(); });
    n.addEventListener("blur", () => { n.value = clamp(n.value); r.value = n.value; onChange(); });
    return () => +r.value;
  }
  const pill = (t, cls) => `<span class="tl-pill${cls ? " " + cls : ""}">${esc(t)}</span>`;

  function initToeic() {
    if (!$("#tc")) return;
    const T = DATA.est || [], AVG = DATA.avg || { total: 686, lc: 378.7, rc: 307.5 };
    const est = n => {
      for (let i = 1; i < T.length; i++) if (n <= T[i][0]) {
        const [a, l1, h1] = T[i - 1], [b, l2, h2] = T[i], r = (n - a) / (b - a);
        return [Math.max(5, Math.round((l1 + (l2 - l1) * r) / 5) * 5), Math.max(5, Math.round((h1 + (h2 - h1) * r) / 5) * 5)];
      }
      return [495, 495];
    };
    let used = false;
    ["lc", "rc"].forEach(k => { const v = QS.get(k); if (v !== null && /^\d{1,3}$/.test(v) && +v <= 100) { $("#tc-" + k).value = v; $("#tc-" + k + "-n").value = v; } });
    const lc = pair("tc-lc", "tc-lc-n", run), rc = pair("tc-rc", "tc-rc-n", run);
    function run() {
      const L = est(lc()), R = est(rc()), lo = L[0] + R[0], hi = L[1] + R[1], mid = (lo + hi) / 2;
      const tot = lo === hi ? `${lo}점` : `${lo}~${hi}점`;
      $("#tc-tot").innerHTML = `<span>${tot}</span>`;
      setShare(`토익 LC ${lc()}개 · RC ${rc()}개 맞히면 예상 점수 ${tot}`, `lc=${lc()}&rc=${rc()}`);
      $("#tc-part").textContent = `LC ${L[0] === L[1] ? L[0] : L[0] + "~" + L[1]} · RC ${R[0] === R[1] ? R[0] : R[0] + "~" + R[1]}`;
      $("#tc-bar").style.width = (mid / 990 * 100).toFixed(1) + "%";
      const d = Math.round(mid - AVG.total), lm = (L[0] + L[1]) / 2, rm = (R[0] + R[1]) / 2;
      $("#tc-pills").innerHTML =
        pill(d >= 0 ? `2025 평균보다 약 ${d}점 높아요` : `2025 평균까지 약 ${-d}점`, "l") +
        pill(lm >= AVG.lc ? "LC 평균 이상" : "LC 평균 아래") + pill(rm >= AVG.rc ? "RC 평균 이상" : "RC 평균 아래");
      if (!used) { used = true; } else if (!run.g) { run.g = 1; ga("tool_use", { tool: "toeic_score" }); }
    }
    run();
  }

  function initOpic() {
    const box = $("#oq"); if (!box) return;
    const G = {}; (DATA.opic || []).forEach(r => { G[r[0]] = { name: r[1], line: r[2], tip: r[3] }; });
    box.addEventListener("click", e => {
      const b = e.target.closest(".tl-can"); if (!b) return;
      $$(".tl-can", box).forEach(x => x.classList.toggle("on", x === b));
      const g = b.dataset.g, key = g === "IM" ? "IM2" : g, info = G[key] || {};
      const label = g === "IM" ? "IM1~IM3" : g;
      $("#oq-out").innerHTML = `<div class="tl-hero-res"><span class="tl-tag">예상 등급 (참고용)</span><p class="tl-big"><span>${esc(label)}</span></p>` +
        `<p class="tl-big-sub">${esc(g === "IM" ? "Intermediate Mid · 말하는 양과 자연스러움에 따라 IM1, IM2, IM3로 나뉘어요" : info.name + " · " + info.line)}</p></div>` +
        `<div class="tl-note"><b>다음 등급으로 가려면</b>${esc(info.tip || "")}</div>` +
        SHARE_ROW + `<a class="tl-more2" href="#g-${esc(key.toLowerCase())}">등급표에서 자세히 보기 ›</a>`;
      $("#oq-out").hidden = false; ga("tool_use", { tool: "opic_level" });
      setShare(`내 오픽 예상 등급은 ${label}`, "g=" + g);
    });
    const g0 = QS.get("g"), b0 = g0 && $(`.tl-can[data-g="${g0.replace(/[^A-Z]/g, "")}"]`, box);
    if (b0) b0.click();
  }

  const TOS = [[200, "AH", "Advanced High"], [180, "AM", "Advanced Mid"], [160, "AL", "Advanced Low"], [140, "IH", "Intermediate High"],
    [130, "IM3", "Intermediate Mid 3"], [120, "IM2", "Intermediate Mid 2"], [110, "IM1", "Intermediate Mid 1"], [90, "IL", "Intermediate Low"],
    [60, "NH", "Novice High"], [0, "NM·NL", "Novice Mid / Low"]];
  function initTos() {
    if (!$("#ts")) return;
    let used = false;
    const s0 = QS.get("s"); if (s0 && /^\d{1,3}$/.test(s0) && +s0 <= 200) { $("#ts").value = s0; $("#ts-n").value = s0; }
    const v = pair("ts", "ts-n", run);
    function run() {
      const s = v(), i = TOS.findIndex(t => s >= t[0]), t = TOS[i], next = TOS[i - 1];
      $("#ts-g").innerHTML = `<span>${esc(t[1])}</span>`; $("#ts-s").textContent = `${s}점 · ${t[2]}`;
      setShare(`토익스피킹 ${s}점은 ${t[1]} 등급`, "s=" + s);
      $("#ts-bar").style.width = (s / 200 * 100) + "%";
      $("#ts-p").innerHTML = (next ? pill(`다음 등급 ${next[1]}까지 ${next[0] - s}점`, "l") : pill("가장 높은 등급이에요", "l")) +
        (/^IM/.test(t[1]) ? pill("IM1~3 점수는 채용 공고에서 흔히 쓰는 기준") : "");
      if (used && !run.g) { run.g = 1; ga("tool_use", { tool: "toeic_speaking" }); } used = true;
    }
    run();
  }

  function initCompare() {
    const L = $("#cp-l"); if (!L) return;
    const rows = DATA.ladder || [];
    const COL = { opic: 1, tos: 2, toeic: 3 }, NAME = { opic: "오픽", tos: "토익스피킹", toeic: "토익" };
    let t = ["opic", "tos", "toeic"].indexOf(QS.get("t")) > -1 ? QS.get("t") : "opic", i = /^\d$/.test(QS.get("i") || "") ? +QS.get("i") : 4;
    $$("#cp-t button").forEach(x => x.classList.toggle("on", x.dataset.t === t));
    const opts = () => rows.map((r, k) => [k, r[COL[t]]]).filter(x => x[1] !== "-");
    function draw() {
      const o = opts(); if (!o.some(x => x[0] === i)) i = o[Math.floor(o.length / 2)][0];
      $("#cp-p").innerHTML = o.map(([k, v]) => `<button type="button" data-i="${k}" class="${k === i ? "on" : ""}">${esc(v.replace(/ \(.*\)/, ""))}</button>`).join("");
      L.innerHTML = '<div class="hd"><span>수준</span><span>오픽</span><span>토스</span><span>토익</span></div>' +
        rows.map((r, k) => `<div class="${k === i ? "on" : ""}${k === i - 1 ? " goal" : ""}"><b>${esc(r[0])}</b><span>${esc(r[1])}</span><span>${esc(r[2])}</span><span>${esc(r[3])}</span></div>`).join("");
      const up = rows[i - 1], me = rows[i];
      const val = x => esc(x.replace(/ \(.*\)/, "")) + (t === "toeic" ? "점" : "");
      $("#cp-y").innerHTML = `${NAME[t]} <b>${val(me[COL[t]])}</b> · <b>${esc(me[0])}</b> 수준` + (up && up[COL[t]] !== "-"
        ? `<br>다음 목표 <b>${val(up[COL[t]])}</b> (점선 칸)` : `<br>이 시험의 가장 높은 단계예요.`);
      setShare(`${NAME[t]} ${me[COL[t]].replace(/ \(.*\)/, "")}${t === "toeic" ? "점" : ""}은 영어 시험 사다리에서 ${me[0]} 수준`, `t=${t}&i=${i}`);
    }
    $("#cp-t").addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return; t = b.dataset.t; $$("#cp-t button").forEach(x => x.classList.toggle("on", x === b)); draw(); });
    $("#cp-p").addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return; i = +b.dataset.i; draw(); ga("tool_use", { tool: "score_compare" }); });
    draw();
  }

  initToeic();
  initOpic();
  initTos();
  initCompare();
  /* =========================================================
     4. 영어 단어 수 세기 — 글은 브라우저 안에서만 세요 (저장·전송 없음)
     ========================================================= */
  function initWordCount() {
    const ta = $("#wc-in"); if (!ta) return;
    const STOP = new Set(("the a an and or but of to in on at for with is are was were be been being it its this that these those i you he she we they my your his our their me him her us them as by from so if not no do does did have has had will would can could should may might must just also there here what which who whom when where why how than then about into over under very really more most some any all each other such only own same too s t can't don't i'm it's").split(" "));
    const EX = "I have always believed that the best way to learn a language is to use it every day. When I started my first job, I had to write emails in English, and I was really nervous about every sentence. I read my emails again and again before I sent them.\n\nOver time, I noticed that my colleagues used short, clear sentences. I started to copy their style, and my emails became much easier to write. Today, English is not a wall for me anymore. It is a window to a bigger world.";
    const fmtT = sec => { sec = Math.round(sec); if (sec < 60) return sec + "초"; const m = Math.floor(sec / 60), r = sec % 60; return r ? `${m}분 ${r}초` : `${m}분`; };
    const N = n => n.toLocaleString("ko-KR");
    const lim = $("#wc-lim");
    let used = false;
    function run() {
      const t = ta.value;
      const words = t.match(/[A-Za-z0-9À-ɏ가-힣]+(?:['’.\-][A-Za-z0-9À-ɏ가-힣]+)*/g) || [];
      const w = words.length;
      const sents = t.split(/[.!?]+(?=\s|$)|\n+/).filter(x => /[A-Za-z0-9가-힣]/.test(x)).length;
      const paras = t.split(/\n+/).filter(x => x.trim()).length;
      $("#wc-w").textContent = N(w);
      $("#wc-c").textContent = N(t.replace(/\n/g, "").length);
      $("#wc-c2").textContent = N(t.replace(/\s/g, "").length);
      $("#wc-s").textContent = N(sents);
      $("#wc-p").textContent = N(paras);
      $("#wc-r").textContent = fmtT(w / 238 * 60);
      $("#wc-sp").textContent = fmtT(w / 150 * 60);
      $("#wc-avg").textContent = sents ? (w / sents).toFixed(1) : "0";
      const L = +lim.value || 0, bar = $("#wc-bar"), lt = $("#wc-lt");
      if (L > 0) {
        bar.style.width = Math.min(100, w / L * 100) + "%"; bar.classList.toggle("over", w > L);
        lt.innerHTML = w > L ? `<b class="bad">${N(w - L)}단어 넘었어요</b> · 제한 ${N(L)}단어` : `<b>${N(L - w)}단어 남았어요</b> · 제한 ${N(L)}단어`;
      } else { bar.style.width = "0"; lt.textContent = "제한을 넣으면 남은 단어 수를 알려 드려요."; }
      const cnt = {};
      words.forEach(x => { const k = x.toLowerCase().replace(/['’].*$/, ""); if (k.length > 2 && /^[a-z]+$/.test(k) && !STOP.has(k)) cnt[k] = (cnt[k] || 0) + 1; });
      const top = Object.entries(cnt).filter(x => x[1] >= 3).sort((a, b) => b[1] - a[1]).slice(0, 6);
      $("#wc-topbox").hidden = !top.length;
      $("#wc-top").innerHTML = top.map(([k, n]) => `<span>${esc(k)} <b>${n}번</b></span>`).join("");
      if (w && !used) { used = true; ga("tool_use", { tool: "word_count" }); }
    }
    ta.addEventListener("input", run); lim.addEventListener("input", run);
    $("#wc-clear").addEventListener("click", () => { ta.value = ""; run(); ta.focus(); });
    $("#wc-ex").addEventListener("click", () => { ta.value = EX; run(); });
    run();
  }

  /* =========================================================
     5. 영어 필기체 — 유니코드 필기체(복사) · 손글씨 글꼴(이미지) · 알파벳 연습지
     ========================================================= */
  function scriptOf(str, bold) {
    const UP = { B: 0x212C, E: 0x2130, F: 0x2131, H: 0x210B, I: 0x2110, L: 0x2112, M: 0x2133, R: 0x211B }, LO = { e: 0x212F, g: 0x210A, o: 0x2134 };
    return Array.from(str).map(c => {
      const u = c.charCodeAt(0);
      if (c >= "A" && c <= "Z") return String.fromCodePoint(bold ? 0x1D4D0 + u - 65 : (UP[c] || 0x1D49C + u - 65));
      if (c >= "a" && c <= "z") return String.fromCodePoint(bold ? 0x1D4EA + u - 97 : (LO[c] || 0x1D4B6 + u - 97));
      return c;
    }).join("");
  }
  function initCursive() {
    const inp = $("#cv-in"); if (!inp) return;
    const FONTS = DATA.fonts || [];
    let font = FONTS[0] ? FONTS[0][0] : "cursive", used = false;
    const val = () => inp.value.trim() || "Cafe in English";
    function copyTab() {
      const v = val(), a = scriptOf(v, false), b = scriptOf(v, true);
      $("#cv-copy").innerHTML = [[a, "필기체"], [b, "굵은 필기체"]].map(([x, n], k) =>
        `<div class="tl-cvrow"><p><span class="tl-cvtxt">${esc(x)}</span><small>${n}</small></p><button type="button" class="tl-cp" data-copy="${esc(x)}" data-f="script${k}">복사</button></div>`).join("") +
        '<p class="tl-note2">인스타그램·카톡 프로필에 그대로 붙여 넣을 수 있어요. 한글과 숫자는 그대로 남아요.</p>';
    }
    function imgTab() {
      $("#cv-fonts").innerHTML = FONTS.map(([f, n]) => `<button type="button" class="tl-font${f === font ? " on" : ""}" data-f="${esc(f)}"><span style="font-family:'${esc(f)}',cursive">${esc(val())}</span><small>${esc(n)}</small></button>`).join("");
    }
    function abcTab() {
      $("#cv-abcf").innerHTML = FONTS.map(([f, n]) => `<button type="button" class="${f === font ? "on" : ""}" data-f="${esc(f)}">${esc(n)}</button>`).join("");
      $("#cv-abcg").style.setProperty("--cf", `'${font}',cursive`);
    }
    const all = () => { copyTab(); imgTab(); abcTab(); };
    inp.addEventListener("input", () => { all(); if (!used) { used = true; ga("tool_use", { tool: "cursive" }); } });
    $("#cv-tab").addEventListener("click", e => {
      const b = e.target.closest("button"); if (!b) return;
      $$("#cv-tab button").forEach(x => x.classList.toggle("on", x === b));
      ["copy", "img", "abc"].forEach(k => { $("#cv-" + k).hidden = k !== b.dataset.v; });
    });
    $("#cv-fonts").addEventListener("click", e => { const b = e.target.closest(".tl-font"); if (!b) return; font = b.dataset.f; imgTab(); abcTab(); });
    $("#cv-abcf").addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return; font = b.dataset.f; imgTab(); abcTab(); });
    $("#cv-save").addEventListener("click", async () => {
      const text = val(), W = 1600, H = 800, cv = document.createElement("canvas"); cv.width = W; cv.height = H;
      const c = cv.getContext("2d");
      try { await document.fonts.load(`120px "${font}"`, text); } catch (e) {}
      c.fillStyle = "#fff"; c.fillRect(0, 0, W, H);
      let size = 220; c.font = `${size}px "${font}", cursive`;
      while (c.measureText(text).width > W - 160 && size > 40) { size -= 6; c.font = `${size}px "${font}", cursive`; }
      c.fillStyle = "#191F28"; c.textAlign = "center"; c.textBaseline = "middle"; c.fillText(text, W / 2, H / 2);
      c.font = "600 28px Pretendard, sans-serif"; c.fillStyle = "#B0B8C1"; c.fillText("cafeinenglish.com", W / 2, H - 50);
      const a = document.createElement("a"); a.download = "cursive-" + text.replace(/[^A-Za-z0-9]+/g, "-").slice(0, 30) + ".png";
      a.href = cv.toDataURL("image/png"); document.body.appendChild(a); a.click(); a.remove();
      ga("tool_use", { tool: "cursive_image" }); toast("이미지를 저장했어요");
    });
    $("#cv-print").addEventListener("click", () => {
      document.body.classList.add("print-abc");
      const off = () => { document.body.classList.remove("print-abc"); removeEventListener("afterprint", off); };
      addEventListener("afterprint", off); window.print(); setTimeout(off, 1500);
    });
    all();
  }

  initWordCount();
  initCursive();

  /* =========================================================
     5. 영어 시험 일정 — 오늘(한국 시간) 기준 다음 시험 D-day + 서류 마감에서 거꾸로
     ========================================================= */
  function initExam() {
    const N = $("#ex-n"); if (!N && !$(".ex-link-s[data-ex]")) return;
    const X = DATA.exam || {}, WD = "일월화수목금토", NAME = { toeic: "토익", tos: "토익스피킹", opic: "오픽" };
    const REG = { toeic: "https://exam.toeic.co.kr/receipt/receiptStep1.php", tos: "https://www.toeicswt.co.kr/", opic: "https://www.opic.or.kr/" };
    const goBtn = (t, w, x) => (now >= w.s && now < w.e) ? `<a class="ex-go" href="${REG[t]}" target="_blank" rel="noopener" data-go="${t}">${NAME[t]} 접수하러 가기<i aria-hidden="true">↗</i></a>` : "";
    const DAY = 864e5, now = Date.now();
    const today = new Date(now + 9 * 3600e3).toISOString().slice(0, 10);
    const at = (d, h, m) => Date.parse(`${d}T${String(h).padStart(2, "0")}:${String(m || 0).padStart(2, "0")}:00+09:00`);
    const addD = (d, k) => new Date(Date.parse(d + "T00:00:00Z") + k * DAY).toISOString().slice(0, 10);
    const ymd = d => d.split("-").map(Number);
    const wd = d => { const [y, m, x] = ymd(d); return WD[new Date(Date.UTC(y, m - 1, x)).getUTCDay()]; };
    const L = d => { const [, m, x] = ymd(d); return `${m}월 ${x}일 (${wd(d)})`; };
    const S = d => { const [, m, x] = ymd(d); return `${m}.${x} (${wd(d)})`; };
    const dd = d => Math.round((Date.parse(d + "T00:00:00Z") - Date.parse(today + "T00:00:00Z")) / DAY);
    const dtag = n => n === 0 ? "D-day" : n > 0 ? "D-" + n : "D+" + (-n);
    const nb = x => `<span class="nw">${x}</span>`;
    const hm = (h, m) => (h === 12 && !m ? "낮 12시" : (h < 12 ? "오전 " : "오후 ") + (h > 12 ? h - 12 : h) + "시" + (m ? ` ${m}분` : ""));

    // 시험마다 같은 모양으로: 시험일, 성적일, 접수 창(열림·닫힘)
    function list(t) {
      if (t === "toeic") return (X.toeic || []).map(e => ({ n: e.n, date: e.date, time: "오전 9시 20분", score: e.score,
        wins: [{ k: "정기접수", s: at(e.reg[0], 10), e: at(e.reg[1], 10), et: `${L(e.reg[1])} 오전 10시`, es: `${S(e.reg[1])} 10시`, ed: e.reg[1], sd: e.reg[0] },
               { k: "특별추가접수", s: at(e.add[0], 10), e: at(e.add[1], 13), et: `${L(e.add[1])} 오후 1시`, es: `${S(e.add[1])} 13시`, ed: e.add[1], sd: e.add[0] }] }));
      if (t === "tos") return (X.tos || []).map(e => ({ date: e.date, time: "", score: e.score,
        wins: [{ k: "접수", s: at(e.reg[0], 10), e: at(e.reg[1], 10), et: `${L(e.reg[1])} 오전 10시`, es: `${S(e.reg[1])} 10시`, ed: e.reg[1], sd: e.reg[0] }] }));
      const o = X.opic || { close_days: 2, open_days: 32, score_days: 5 }, out = [];
      for (let k = 0; k < 75; k++) {
        const d = addD(today, k), c = addD(d, -o.close_days);
        out.push({ date: d, time: "", score: addD(d, o.score_days), opic: 1,
          wins: [{ k: "접수", s: Date.parse(addD(d, -o.open_days) + "T00:00:00+09:00"), e: Date.parse(addD(c, 1) + "T00:00:00+09:00"), et: `${L(c)}까지`, es: `${S(c)}까지`, ed: c, sd: addD(d, -o.open_days) }] });
      }
      return out;
    }
    // 지금 열려 있거나 앞으로 열릴 접수 창
    const openWin = x => x.wins.find(w => now < w.e);
    function status(x) {
      const w = openWin(x);
      if (!w) return { cls: "x", t: "접수 마감" };
      if (now < w.s) return { cls: "", t: `${S(w.sd || today).replace(/ \(.\)/, "")} 시작` };
      const left = dd(w.ed);
      return left <= 3 ? { cls: "r", t: (left <= 0 ? "오늘" : "D-" + left) + " 마감" } : { cls: "l", t: w.k === "특별추가접수" ? "특별추가 중" : "접수 중" };
    }
    const pillH = st => `<span class="ex-pill ${st.cls}">${esc(st.t)}</span>`;

    // 다른 시험 도구의 '다음 시험 일정' 줄
    $$(".ex-link-s[data-ex]").forEach(el => {
      const x = list(el.dataset.ex).filter(y => y.date >= today && openWin(y))[0]; if (!x) return;
      const w = openWin(x), left = dd(w.ed);
      el.textContent = `${L(x.date)} 시험 · ` + (now < w.s ? `${S(w.sd)} 접수 시작` : `${w.k === "특별추가접수" ? "특별추가 " : ""}접수 마감 ${left <= 0 ? "오늘" : "D-" + left}`);
    });
    if (!N) return;
    document.addEventListener("click", e => { const a = e.target.closest("[data-go]"); if (a) ga("tool_out", { tool: "test_schedule", exam: a.dataset.go }); });
    let T = ["toeic", "tos", "opic"].indexOf(QS.get("t")) > -1 ? QS.get("t") : "toeic";
    function draw() {
      $$("#ex-t button").forEach(b => b.classList.toggle("on", b.dataset.t === T));
      const all = list(T).filter(x => x.date >= today), live = all.filter(openWin);
      const hero = live[0];
      if (!hero) {
        N.innerHTML = `<p class="ex-tg">다음 ${NAME[T]}</p><p class="ex-big">일정 준비 중</p><p class="ex-sub">새 일정이 발표되면 바로 올려 드릴게요.</p>`;
        $("#ex-l").innerHTML = ""; $("#ex-l").hidden = true; return;
      }
      const w = openWin(hero), left = dd(w.ed), pre = now < w.s;
      const reg = hero.wins[0], regDone = T === "toeic" && now >= reg.e;
      N.innerHTML = `<p class="ex-tg">${T === "opic" ? "가장 빨리 볼 수 있는 오픽" : "다음 " + NAME[T] + (hero.n ? ` · 제${hero.n}회` : "") + (hero.time ? ` · ${hero.time.replace("오전 9시 20분", "오전 9:20")} 시험` : "")}</p>` +
        `<p class="ex-big"><span>${dtag(dd(hero.date))}</span> ${L(hero.date)}</p>` +
        `<p class="ex-sub">성적 발표 ${nb(L(hero.score) + (hero.opic ? " 무렵" : " 낮 12시"))}</p>` +
        `<div class="ex-dl${left <= 3 && !pre ? " hot" : ""}"><i>${pre ? "예정" : left <= 0 ? "오늘" : "D-" + left}</i><p>${pre ? `${nb(L(w.sd) + " 오전 10시")} 접수 시작` : `${nb(w.et.replace(/까지$/, ""))} 마감`}` +
        `<small>${esc(w.k)}${regDone ? " · 정기접수보다 응시료가 비싸요" : hero.opic ? " · 고사장마다 시험 시간이 달라요" : pre ? ` · 마감 ${w.et}` : " · 시간이 지나면 접수할 수 없어요"}</small></p></div>` + goBtn(T, w, hero);
      const rows = (T === "opic" ? live.filter(x => x !== hero && /[토일]/.test(wd(x.date))) : live.filter(x => x !== hero)).slice(0, T === "opic" ? 4 : 6);
      $("#ex-l").hidden = !rows.length;
      $("#ex-l").innerHTML = (T === "opic" ? '<p class="ex-lh">주말 오픽</p>' : "") + rows.map(x => {
        const ww = openWin(x) || x.wins[x.wins.length - 1];
        return `<div class="ex-row"><b>${S(x.date).replace(/ \((.)\)/, " <small>($1)</small>")}</b><span>${ww.k === "특별추가접수" ? "특별추가" : "접수"} <b class="nw">~${ww.es}</b><br>성적 ${S(x.score)}</span>${pillH(status(x))}</div>`;
      }).join("");
      if (!draw.f) setShare(`다음 ${NAME[T]} ${L(hero.date)}, ${w.k} 마감 ${w.et}`, "t=" + T);
    }

    // 서류 마감에서 거꾸로
    const D = $("#ex-d"), R = $("#ex-r");
    D.min = today;
    const n0 = QS.get("need");
    D.value = n0 && /^\d{4}-\d\d-\d\d$/.test(n0) && n0 >= today ? n0 : addD(today, 30);
    function back() {
      const need = D.value; if (!need) { R.innerHTML = ""; return; }
      const lines = [];
      R.innerHTML = ["toeic", "tos", "opic"].map(t => {
        const ok = list(t).filter(x => x.date >= today && openWin(x) && x.score <= need), last = ok[ok.length - 1];
        const lastAny = list(t).slice(-1)[0];
        if (!last) {
          const first = list(t).filter(x => x.date >= today && openWin(x))[0];
          return `<div class="tl-box ex-res"><p class="ex-rh">${NAME[t]}<span class="ex-pill x">어려워요</span></p><p class="ex-rb">이 날짜까지는 성적이 안 나와요</p>` +
            `<p class="ex-rs">${first ? `가장 빠른 성적은 ${S(first.score)} (${S(first.date)} 시험)` : "새 일정이 발표되면 알려 드릴게요"}</p></div>`;
        }
        const w = openWin(last), st = status(last), beyond = t !== "opic" && lastAny && need > lastAny.score;
        lines.push(`${NAME[t]} ${S(last.date)}`);
        return `<div class="tl-box ex-res"><p class="ex-rh">${NAME[t]}${pillH(st)}</p><p class="ex-rb"><span>${L(last.date)}</span>${t === "opic" ? "까지" : " 시험이 마지막"}</p>` +
          `<p class="ex-rs">성적 ${S(last.score)} · ${esc(w.k)} ${nb(w.et + (t === "opic" ? "" : "까지"))}${beyond ? `<br>${X.toeic_year + 1}년 일정은 발표되면 더해요` : ""}</p>${(now >= w.s && now < w.e) ? `<a class="ex-go2" href="${REG[t]}" target="_blank" rel="noopener" data-go="${t}">공식 사이트에서 접수 ↗</a>` : ""}</div>`;
      }).join("");
      if (draw.f) setShare(`${L(need)}까지 영어 성적이 필요하면 마지막 기회는 ${lines.join(", ")} 시험`, "need=" + need);
    }
    $("#ex-t").addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return; T = b.dataset.t; draw.f = 0; draw(); ga("tool_use", { tool: "test_schedule" }); });
    D.addEventListener("change", () => { draw.f = 1; back(); ga("tool_use", { tool: "test_schedule_back" }); });
    $("#ex-qp").addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return; D.value = addD(today, +b.dataset.w); draw.f = 1; back(); });
    if (n0) draw.f = 1;
    draw(); back();
    // 표: 지난 시험은 흐리게
    const seen = {};
    $$(".ex-tile").forEach(el => {
      const k = el.dataset.exT, x = list(k).find(y => y.date === el.dataset.d), p = $(".ex-tp", el); if (!x) return;
      if (x.date < today || !openWin(x)) { el.hidden = true; return; }  // 지난 시험·접수 끝난 시험은 숨김 (검색용 HTML에는 그대로)
      const st = status(x); p.textContent = st.t; p.className = "ex-tp " + st.cls;
      if (!seen[k]) { seen[k] = 1; el.classList.add("next"); }
    });
    $$(".ex-grid").forEach(g => {  // 토익스피킹처럼 긴 목록은 6개만 먼저
      const btn = g.nextElementSibling; if (!btn || !btn.classList.contains("ex-more")) return;
      const vis = $$(".ex-tile", g).filter(el => !el.hidden); if (vis.length <= 6) return;
      vis.slice(6).forEach(el => el.classList.add("ex-fold"));
      btn.hidden = false; btn.textContent = `일정 더 보기 (${vis.length - 6})`;
      btn.addEventListener("click", () => { $$(".ex-fold", g).forEach(el => el.classList.remove("ex-fold")); btn.hidden = true; });
    });
  }
  initExam();

  /* 영어 도구 목록: 휴대폰 세그먼트 → 오른쪽 '보기' 필터와 같이 움직이게 */
  (function () {
    const seg = $(".tool-seg"); if (!seg) return;
    seg.addEventListener("click", e => {
      const b = e.target.closest("button"); if (!b) return;
      $$("button", seg).forEach(x => { const on = x === b; x.classList.toggle("on", on); x.setAttribute("aria-selected", on ? "true" : "false"); });
      const f = $(`.subfilter .sf-b[data-sub="${b.dataset.sub}"]`); if (f) f.click();
    });
  })();
})();
