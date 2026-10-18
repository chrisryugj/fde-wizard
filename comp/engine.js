// 합성 엔진: render(f) 가 프레임 f(0부터)의 화면을 결정적으로 그린다. 타임라인은 TL[video].
const R = '../' + (new URLSearchParams(location.search).get('root') || 'renders') + '/';
const pad = n => String(n).padStart(4, '0');
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const prog = (f, a, b) => clamp((f - a) / (b - a), 0, 1);
const E = {
  out: t => 1 - Math.pow(1 - t, 3),
  back: t => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  inOut: t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
};
const $ = id => document.getElementById(id);
let pending = [];

function layer(i, src, frame, o = {}) {
  const el = $('L' + i);
  if (!src) { el.classList.add('hide'); return; }
  el.classList.remove('hide');
  const url = R + src + '/' + pad(frame) + '.png';
  if (el.dataset.url !== url) { el.src = url; el.dataset.url = url; pending.push(el); }
  el.style.opacity = o.opacity ?? 1;
  el.style.clipPath = o.clipBottom ? `inset(0 0 ${o.clipBottom}px 0)` : 'none';
  el.style.filter = o.filter || 'none';
  el.style.transform = o.transform || 'none';
}
function show(id, on) { $(id).classList.toggle('hide', !on); }
function cue(list, f) { let c = null; for (const x of list) if (f >= x[0]) c = x; return c; }

// ---------------------------------------------------------------- 영상 A: 제작영상
const A = {
  segs: [
    { id: 'cold', dur: 90, shot: 'a01_cold', n: 90 },
    { id: 'photo', dur: 45 },
    { id: 'assem', dur: 90, shot: 'a03_assemble', pass: 'clay', n: 84 },
    { id: 'turn', dur: 90, shot: 'a04_turntable', n: 96 },
    { id: 'rig', dur: 60, shot: 'a05_rig', n: 54 },
    { id: 'rtest', dur: 120, shot: 'a06_rigtest', n: 120 },
    { id: 'poses', dur: 90, shot: 'a07_poses', n: 90 },
    { id: 'wave', dur: 60, shot: 'a08_wave', n: 60 },
    { id: 'bow', dur: 75, shot: 'a09_bow', n: 72 },
    { id: 'cast', dur: 105, shot: 'a10_cast', n: 105 },
    { id: 'end', dur: 135, shot: 'a11_end', n: 135 },
  ],
  steps: [[90, 1, '모델'], [315, 2, '리그'], [495, 3, '포즈'], [585, 4, '애니메이트'], [825, 0, '']],
  // 자막이 말하는 내용은 꼬리표로 겹쳐 쓰지 않는다 — 화면 상태 이름만
  tags: [[90, ''], [225, '와이어프레임'], [259, '클레이'], [289, '컬러'], [315, ''],
         [375, '테스트: 손 흔들기'], [414, '테스트: 걷기'], [454, '테스트: 인사'], [495, ''], [825, '']],
  code: [
    ['c', '# params.py — 한 사람분 데이터, 숫자만 고치면 다시 빌드\n'],
    ['k', 'HEAD'], ['p', ' = {'], ['s', "'radius'"], ['p', ': ('], ['n', '0.53, 0.48, 0.475'], ['p', ')}\n'],
    ['k', 'FACE'], ['p', ' = {'], ['s', "'eye_smile'"], ['p', ': '], ['n', '0.42'], ['p', ', '], ['s', "'brow_r'"], ['p', ': '], ['n', '0.019'], ['p', '}\n'],
    ['k', 'HAIR_LOCKS'], ['p', ' = {'], ['s', "'swoop_a'"], ['p', ': [('], ['n', '-22, 33'], ['p', '), ...]}\n'],
    ['k', 'COLORS'], ['p', ' = {'], ['s', "'suit'"], ['p', ': '], ['s', "'#141A35'"], ['p', ', '], ['s', "'tie_dot'"], ['p', ': '], ['s', "'#E8ECF6'"], ['p', '}\n'],
    ['k', 'HAT'], ['p', ' = {'], ['s', "'tilt'"], ['p', ': ('], ['n', '-12, -6'], ['p', '), '], ['s', "'stars'"], ['p', ': ['], ['n', '5'], ['p', ' 개]}'],
  ],
};

function codeHTML(nChars) {
  let out = '<div class="hd">Claude Code가 쓴 Blender Python</div>', used = 0;
  for (const [cls, txt] of A.code) {
    if (used >= nChars) break;
    const t = txt.slice(0, nChars - used);
    used += t.length;
    const esc = t.replace(/&/g, '&amp;').replace(/</g, '&lt;');
    out += cls === 'p' ? esc : `<span class="${cls}">${esc}</span>`;
  }
  return out + '<span class="cur"></span>';
}
const CODE_LEN = A.code.reduce((s, [, t]) => s + t.length, 0);

function shelfInit() {
  const sh = $('shelf');
  if (sh.dataset.ok) return;
  const labels = ['인사', '손인사', '주문', '엄지척', '짠!', '생각'];
  labels.forEach((l, i) => {
    const d = document.createElement('div');
    d.className = 'it';
    d.innerHTML = `<img src="${R}A/a07_thumbs/beauty/${pad(i + 1)}.png"><span>${l}</span>`;
    sh.appendChild(d);
  });
  sh.dataset.ok = 1;
}

function drawA(f) {
  let start = 0, seg = null;
  for (const s of A.segs) { if (f < start + s.dur) { seg = s; break; } start += s.dur; }
  if (!seg) { seg = A.segs[A.segs.length - 1]; start = 960 - seg.dur; }
  const l = f - start;
  const fr = seg.n ? Math.min(l + 1, seg.n) : 1;
  for (let i = 0; i < 4; i++) layer(i, null);
  ['scan', 'photoCard', 'code', 'shelf', 'cursor', 'bubble', 'endCard', 'headline'].forEach(id => show(id, false));
  $('ripple').style.opacity = 0;
  const S = seg.shot ? `A/${seg.shot}/` : '';

  if (seg.id === 'cold') {
    layer(0, S + 'beauty', fr);
    show('headline', l < 88);
    const t = E.out(prog(l, 0, 10)), u = prog(l, 82, 90);
    $('headline').style.transform = `translateY(${(-1 + t) * 60 - u * 80}px)`;
    $('headline').style.opacity = t * (1 - u);
  } else if (seg.id === 'photo') {
    show('photoCard', true); show('code', l > 4);
    const p = E.back(prog(l, 0, 10));
    $('photoCard').style.transform = `scale(${0.7 + 0.3 * p}) rotate(${(1 - p) * -4}deg)`;
    $('photoCard').style.opacity = prog(l, 0, 4);
    const sy = E.inOut(prog(l, 12, 40)) * 600;
    $('scanBox').querySelector('.bar').style.top = sy + 'px';
    $('scanBox').querySelector('.grid').style.height = sy + 'px';
    $('code').innerHTML = codeHTML(Math.round(CODE_LEN * prog(l, 6, 40)));
    const c = E.out(prog(l, 4, 12));
    $('code').style.transform = `translateX(${(1 - c) * 80}px)`;
    $('code').style.opacity = c;
  } else if (seg.id === 'assem') {
    layer(0, S + 'clay', fr);
  } else if (seg.id === 'turn') {
    layer(0, S + 'wire', fr);
    const w1 = E.inOut(prog(l, 28, 40)), w2 = E.inOut(prog(l, 58, 70));
    if (l >= 28) layer(1, S + 'clay', fr, { clipBottom: (1 - w1) * 1080 });
    if (l >= 58) layer(2, S + 'beauty', fr, { clipBottom: (1 - w2) * 1080 });
    const sw = (l >= 28 && l < 41) ? w1 : (l >= 58 && l < 71) ? w2 : -1;
    show('scan', sw >= 0 && sw < 1);
    $('scan').style.top = (sw * 1080 - 3) + 'px';
  } else if (seg.id === 'rig' || seg.id === 'rtest') {
    layer(0, S + 'clay', fr);
    layer(1, S + 'bones', fr, { filter: 'drop-shadow(0 0 3px rgba(255,160,70,.95)) drop-shadow(0 0 10px rgba(255,140,40,.5))' });
  } else if (seg.id === 'poses') {
    layer(0, S + 'beauty', fr);
    shelfInit(); show('shelf', true); show('cursor', true);
    const snaps = [6, 20, 34, 48, 62, 76];
    let act = -1;
    snaps.forEach((s, i) => { if (l + 1 >= s) act = i; });
    [...$('shelf').querySelectorAll('.it')].forEach((d, i) => {
      d.classList.toggle('on', i === act);
      d.style.transform = i === act ? `scale(${1 + 0.06 * (1 - prog(l + 1, snaps[i], snaps[i] + 6))})` : 'none';
    });
    // 커서: 다음 항목으로 6프레임 동안 이동 → 스냅 프레임에 클릭
    const items = [...$('shelf').querySelectorAll('.it')];
    const pos = i => { const r = items[clamp(i, 0, 5)].getBoundingClientRect(); return [r.left + 70, r.top + 60]; };
    let ci = snaps.findIndex(s => l + 1 < s); if (ci < 0) ci = 5;
    const from = pos(ci - 1 < 0 ? 0 : ci - 1), to = pos(ci);
    const mv = E.inOut(prog(l + 1, snaps[ci] - 7, snaps[ci] - 1));
    const x = from[0] + (to[0] - from[0]) * mv, y = from[1] + (to[1] - from[1]) * mv - (ci === 0 ? (1 - mv) * 120 : 0);
    const click = Math.abs(l + 1 - snaps[ci]) < 2 || (act >= 0 && l + 1 - snaps[act] < 2);
    $('cursor').style.left = x + 'px'; $('cursor').style.top = y + 'px';
    $('cursor').style.transform = `scale(${click ? 0.82 : 1})`;
    if (act >= 0) {
      const rp = prog(l + 1, snaps[act], snaps[act] + 8);
      const p = pos(act);
      $('ripple').style.left = p[0] + 'px'; $('ripple').style.top = p[1] + 'px';
      $('ripple').style.opacity = rp < 1 ? 1 - rp : 0;
      $('ripple').style.transform = `scale(${0.4 + rp * 1.2})`;
    }
  } else if (seg.id === 'wave' || seg.id === 'cast') {
    layer(0, S + 'beauty', fr);
    if (seg.id === 'cast' && l >= 74 && l < 100) bubble('짠!', 1235, 330, l - 74, 26);
  } else if (seg.id === 'bow') {
    layer(0, S + 'beauty', fr);
    if (l >= 24 && l < 44) bubble('앗, 모자!', 1190, 200, l - 24, 20);
  } else if (seg.id === 'end') {
    layer(0, S + 'beauty', fr);
    show('endCard', true);
    if (!$('ecM').dataset.ok) {
      $('ecM').src = 'thumbs/model.jpg'; $('ecR').src = 'thumbs/rig.jpg'; $('ecA').src = 'thumbs/anim.jpg';
      $('ecM').dataset.ok = 1;
      pending.push($('ecM'), $('ecR'), $('ecA'));
    }
    const p = E.out(prog(l, 0, 14));
    $('endCard').style.transform = `translateX(${(1 - p) * -120}px)`;
    $('endCard').style.opacity = p;
    [...$('endCard').querySelectorAll('.row div')].forEach((d, i) => {
      const q = E.back(prog(l, 8 + i * 5, 18 + i * 5));
      d.style.transform = `translateY(${(1 - q) * 30}px)`; d.style.opacity = prog(l, 8 + i * 5, 14 + i * 5);
    });
  }
  // 단계별 실제 코드 한 줄(오른쪽 아래)
  const CH = {1: [['k', 'sweep'], ['p', "('swoop_a', spine, radius="], ['s', '0.215'], ['p', ')'], ['c', '  # 머리 웨이브']],
              2: [['p', 'ik = pb.constraints.new('], ['s', "'IK'"], ['p', '); ik.chain_count = '], ['s', '2']],
              3: [['k', 'poses.apply'], ['p', '(rig, '], ['s', "'tada'"], ['p', ')'], ['c', '  # 원클릭 포즈']],
              4: [['k', 'anim.bake_springs'], ['p', '(rig, 1, 105)'], ['c', '  # 모자·망토 흔들림']]};
  const stc = cue([[135, 1], [315, 2], [495, 3], [585, 4], [825, 0]], f);
  const chipOn = stc && stc[1] > 0 && f >= 135;
  show('chip', chipOn);
  if (chipOn) {
    const parts = CH[stc[1]], total = parts.reduce((a, [, x]) => a + x.length, 0);
    let n = Math.round(total * prog(f, stc[0] + 4, stc[0] + 20)), html = '<div class="hd">BLENDER PYTHON · CLAUDE CODE</div>';
    for (const [cls, txt] of parts) { if (n <= 0) break; const t = txt.slice(0, n); n -= t.length;
      html += cls === 'p' ? t : `<span class="${cls}">${t}</span>`; }
    $('chip').innerHTML = html;
    $('chip').style.opacity = prog(f, stc[0] + 1, stc[0] + 5);
  }
  // 단계 알약 + 꼬리표
  const st = cue(A.steps, f), tg = cue(A.tags, f);
  const stOn = st && st[1] > 0;
  show('step', stOn); show('tag', !!(tg && tg[1]) && stOn);
  if (stOn) {
    $('step').querySelector('.num').textContent = st[1];
    $('step').querySelector('.name').textContent = st[2];
    const p = E.back(prog(f, st[0], st[0] + 8));
    $('step').style.transform = `scale(${0.7 + 0.3 * p})`;
    $('step').style.opacity = prog(f, st[0], st[0] + 3);
  }
  if (tg && tg[1] && stOn) {
    $('tag').textContent = tg[1];
    const p = E.out(prog(f, tg[0], tg[0] + 7));
    $('tag').style.transform = `translateX(${(1 - p) * -40}px)`;
    $('tag').style.opacity = p;
  }
  subtitles(f, window.NARR_A || []);
  // 컷 번쩍
  const flashAt = [90, 135, 825];
  let fl = 0;
  for (const c of flashAt) if (f >= c && f < c + 6) fl = Math.max(fl, 0.75 * (1 - (f - c) / 6));
  $('flash').style.opacity = fl;
}

function subtitles(f, cues) {
  const t = f / 30, el = $('sub');
  let on = null, a = 0, b = 0;
  cues.forEach(([st, d, text], i) => {
    const nx = i + 1 < cues.length ? cues[i + 1][0] : 1e9;
    const s0 = st - 0.05, s1 = Math.min(st + d + 0.35, nx - 0.08);
    if (t >= s0 && t < s1) { on = text; a = s0; b = s1; }
  });
  show('sub', !!on);
  if (!on) return;
  if (el.dataset.text !== on) { el.textContent = on; el.dataset.text = on; }
  const fin = clamp((t - a) / 0.3, 0, 1), fout = clamp((b - t) / 0.3, 0, 1);
  const k = Math.min(fin, fout);
  el.style.opacity = k;
  el.style.transform = `translateX(-50%) translateY(${(1 - E.out(fin)) * 14 - (1 - fout) * 14}px)`;
}

function bubble(text, x, y, t, life) {
  show('bubble', true);
  const b = $('bubble');
  b.textContent = text;
  b.style.left = x + 'px'; b.style.top = y + 'px';
  const p = E.back(prog(t, 0, 6)), q = prog(t, life - 4, life);
  b.style.transform = `scale(${(0.4 + 0.6 * p) * (1 - q * 0.4)})`;
  b.style.opacity = 1 - q;
}

// ---------------------------------------------------------------- 영상 B: 공공AX
const B = {
  segs: [
    { id: 'intro', dur: 90, shot: 'b01_intro', n: 90 }, { id: 'docs', dur: 240, shot: 'b02_docs', n: 240 },
    { id: 'law', dur: 240, shot: 'b03_law', n: 240 }, { id: 'map', dur: 240, shot: 'b04_map', n: 240 },
    { id: 'share', dur: 210, shot: 'b05_share', n: 210 }, { id: 'outro', dur: 150, shot: 'b06_outro', n: 150 },
  ],
  chapters: [[90, '01', '한글 문서 → 데이터'], [330, '02', 'AI 답은 초안'], [570, '03', '동네를 데이터로'], [810, '04', '마법은 나눌수록'], [1020, '', '']],
  caps: [
    [100, 196, '보고서·공문·서식, <em>산더미 같은 한글 문서</em>', ''],
    [206, 330, '<em>kordoc</em>이 읽어서 바로 쓰는 데이터로', 'HWP·HWPX·PDF 파싱 오픈소스 · npm 누적 35만+'],
    [340, 470, 'AI가 내놓은 그럴듯한 답, <em>그대로 써도 될까?</em>', ''],
    [480, 570, '<em>법령 원문</em>과 대조해서 검증', 'korean-law-mcp · 법제처 원문 조회 · GitHub ★ 2,729'],
    [580, 700, '우리 동네 문제는 <em>어디서, 얼마나?</em>', ''],
    [710, 810, '<em>지도 위 데이터</em>로 한눈에', '무단투기·인파·생활 상황판'],
    [830, 1020, '<em>오픈소스</em>로 나누면, 다른 기관도 바로 쓴다', 'GitHub ★ 6,579 · 2026. 10. 18. 기준'],
  ],
  cuts: [90, 330, 570, 810, 1020],
};

function narrCaps(cues) {  // [시작 초, 말 길이, 자막 html, 작은 줄] → [시작 프레임, 끝 프레임, html, 작은 줄]
  return cues.map(([st, d, html, small], i) => {
    const nx = i + 1 < cues.length ? cues[i + 1][0] : 1e9;
    return [Math.round((st - 0.05) * 30), Math.round(Math.min(st + d + 0.35, nx - 0.08) * 30), html, small];
  }).filter(x => x[2]);
}

function drawB(f) {
  let start = 0, seg = null;
  for (const s of B.segs) { if (f < start + s.dur) { seg = s; break; } start += s.dur; }
  if (!seg) { seg = B.segs[B.segs.length - 1]; start = 1170 - seg.dur; }
  const l = f - start, fr = Math.min(l + 1, seg.n);
  for (let i = 0; i < 4; i++) layer(i, null);
  ['scan', 'photoCard', 'code', 'shelf', 'cursor', 'bubble', 'endCard', 'headline', 'step', 'tag'].forEach(id => show(id, false));
  $('ripple').style.opacity = 0;
  layer(0, `B/${seg.shot}/beauty`, fr);
  $('vignette').style.background = 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(8,6,30,.38) 100%)';
  // 챕터
  const ch = cue(B.chapters, f);
  show('chapter', !!(ch && ch[1]));
  if (ch && ch[1]) {
    $('chapter').querySelector('.no').textContent = ch[1];
    $('chapter').querySelector('.tt').textContent = ch[2];
    const p = E.back(prog(f, ch[0], ch[0] + 9));
    $('chapter').style.transform = `translateX(${(1 - p) * -60}px)`;
    $('chapter').style.opacity = prog(f, ch[0], ch[0] + 4);
  }
  // 자막: 내레이션이 있으면 말하는 동안만, 없으면 B.caps
  const c = (window.NARR_B ? narrCaps(window.NARR_B) : B.caps).find(x => f >= x[0] && f < x[1]);
  show('cap', !!c);
  if (c) {
    $('cap').innerHTML = c[2] + (c[3] ? `<small>${c[3]}</small>` : '');
    const p = E.out(prog(f, c[0], c[0] + 8)), q = prog(f, c[1] - 6, c[1]);
    $('cap').style.transform = `translateX(-50%) translateY(${(1 - p) * 30 + q * 20}px)`;
    $('cap').style.opacity = p * (1 - q);
  }
  // 타이틀(출동 / 마무리)
  const T = $('title');
  if (seg.id === 'intro' && l >= 44) {
    show('title', true);
    T.querySelector('.k').textContent = '공공AX FDE';
    T.querySelector('.m').textContent = '현장으로 출동!';
    T.querySelector('.s').textContent = '';
    const p = E.back(prog(l, 44, 54)), q = prog(l, 84, 90);
    T.style.transform = `translate(-540px, ${-300 + (1 - p) * 40}px) scale(${0.85 + 0.15 * p})`;  // 왼쪽 위 하늘(캐릭터와 안 겹치게)
    T.style.opacity = prog(l, 44, 48) * (1 - q);
  } else if (seg.id === 'outro' && l >= 56) {
    show('title', true);
    T.querySelector('.k').textContent = '공공AX FDE';
    T.querySelector('.m').textContent = '광진구청 류승인 주무관';
    T.querySelector('.s').textContent = 'AI 답은 초안, 판단은 사람이';
    const p = E.out(prog(l, 56, 70));
    T.style.transform = `translateX(-430px) translateY(${-150 + (1 - p) * 30}px)`;  // 건물 지붕 위 하늘로
    T.style.opacity = p;
  } else show('title', false);
  // ★ 카운터(별이 섬에 닿을 때마다)
  if (seg.id === 'share') {
    show('counter', true);
    const arr = [54, 63, 72, 81, 90, 99, 108, 117];
    let k = 0; arr.forEach(a => { if (l + 1 >= a) k++; });
    const target = Math.round(6579 * k / arr.length);
    const prevT = Math.round(6579 * Math.max(0, k - 1) / arr.length);
    const last = k ? arr[k - 1] : 0;
    const v = k ? Math.round(prevT + (target - prevT) * E.out(prog(l + 1, last, last + 6))) : 0;
    $('counter').querySelector('b').textContent = v.toLocaleString('en-US');
    const p = E.back(prog(l, 40, 50));
    $('counter').style.transform = `scale(${0.6 + 0.4 * p})`;
    $('counter').style.opacity = prog(l, 40, 44);
    $('counter').querySelector('.pulse').style.opacity = (k && l + 1 - last < 6) ? 1 - (l + 1 - last) / 6 : 0;
  } else show('counter', false);
  let fl = 0;
  for (const cc of B.cuts) if (f >= cc && f < cc + 5) fl = Math.max(fl, 0.55 * (1 - (f - cc) / 5));
  $('flash').style.opacity = fl;
}

const TL = { A: { total: 960, draw: drawA }, B: { total: 1170, draw: drawB } };
window.render = async (video, f) => {
  pending = [];
  TL[video].draw(f);
  await document.fonts.ready;
  await Promise.all(pending.map(el => el.decode().catch(() => {})));
  return true;
};
window.TL = TL;
