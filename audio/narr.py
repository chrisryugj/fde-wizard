"""영상 A·B 내레이션: 대본(시작 초·자막·작은 줄·읽기) → ElevenLabs 진건 송(eleven_v4) → 다듬기
→ audio/out/narr{V}/NN.wav, audio/out/narr{V}/cues.json, comp/narr_{V}.js
python narr.py A|B [속도(기본 1.2)]   ※ 받은 mp3 는 el/ 에 캐시 — 문장을 고치면 그 번호 mp3 를 지울 것"""
import getpass
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = 'BbsagRO6ohd8MKPS2Ob0'  # 진건 송
FF = 'ffmpeg'

# (시작 초, 화면 자막, 자막 아래 작은 줄, 읽을 문장). 시작은 컷 직후 0.1~0.3초, 효과음 '쾅' 직후.
# B 자막은 <em> 강조를 쓰고, 자막이 '' 이면 말만 하고 자막은 안 띄운다(화면에 같은 글이 이미 있을 때).
CUES = {
    'A': (32.0, [  # 컷: 3.0 4.5 7.5 10.5 12.5 16.5 19.5 21.5 24.0 27.5
        (0.15, '광진구청 주무관을 마법사로 만들어 봤습니다', '', '광진구청 주무관을 마법사로 만들어 봤습니다.'),
        (3.05, '보고 만든 건 사진 한 장', '', '보고 만든 건, 사진 한 장.'),
        (5.08, '부품 69개를 코드로 붙였습니다', '', '부품 예순아홉 개를 코드로 붙였습니다.'),
        (7.65, '치수와 색은 파일 하나에 숫자로 들어 있습니다', '', '치수와 색은 파일 하나에 숫자로 들어 있습니다.'),
        (10.65, '뼈는 44개', '', '뼈는 마흔네 개.'),
        (12.65, '손발 끝만 옮기면 팔다리가 따라옵니다. 걷는 것도요', '', '손발 끝만 옮기면 팔다리가 따라옵니다. 걷는 것도요.'),
        (16.65, '자세는 목록에서 고르면 됩니다', '', '자세는 목록에서 고르면 됩니다.'),
        (19.55, '모자와 망토는 알아서 흔들리고', '', '모자와 망토는 알아서 흔들리고,'),
        (21.95, '인사하면 모자가 미끄러집니다', '', '인사하면 모자가 미끄러집니다.'),
        (24.70, '주문을 외우면 곰돌이가 나옵니다', '', '주문을 외우면, 곰돌이가 나옵니다.'),
        (27.65, '처음부터 끝까지, Claude Code가 쓴 Blender Python입니다', '', '처음부터 끝까지, 클로드 코드가 쓴 블렌더 파이썬입니다.'),
    ]),
    'B': (39.0, [  # 장: 출동 0 · 문서 3.0 · 법령 11.0 · 지도 19.0 · 오픈소스 27.0 · 마무리 34.0
        (1.75, '마법사 공무원이 <em>현장</em>에 출동했습니다', '', '마법사 공무원이 현장에 출동했습니다.'),
        (4.05, '보고서, 공문, 서식. <em>한글 문서가 산더미</em>예요', '', '보고서, 공문, 서식. 한글 문서가 산더미예요.'),
        (8.0, '<em>kordoc</em>이 읽으면, 바로 쓰는 데이터가 됩니다', 'HWP·HWPX·PDF 파싱 오픈소스 · npm 누적 35만+',
         '코닥이 읽으면, 바로 쓰는 데이터가 됩니다.'),
        (11.5, 'AI가 내놓은 그럴듯한 답, <em>그대로 써도 될까요?</em>', '', '에이아이가 내놓은 그럴듯한 답, 그대로 써도 될까요?'),
        (15.0, '<em>법령 원문</em>과 대조하면, 틀린 데가 보입니다', 'korean-law-mcp · 법제처 원문 조회 · GitHub ★ 2,729',
         '법령 원문과 대조하면, 틀린 데가 보입니다.'),
        (19.2, '동네 문제는 <em>어디서, 얼마나</em> 생길까요?', '', '동네 문제는 어디서, 얼마나 생길까요?'),
        (22.2, '<em>지도</em>에 데이터를 띄우면, 한눈에 보입니다', '무단투기·인파·생활 상황판', '지도에 데이터를 띄우면, 한눈에 보입니다.'),
        (27.5, '이 마법은 전부 <em>오픈소스</em>로 나눴습니다', '', '이 마법은 전부 오픈소스로 나눴습니다.'),
        (30.4, '그러면 <em>다른 기관도 바로</em> 가져다 씁니다', 'GitHub ★ 6,579 · 2026. 10. 18. 기준', '그러면 다른 기관도 바로 가져다 씁니다.'),
        (36.25, '', '', '판단은, 사람이 합니다.'),  # 마무리 타이틀에 'AI 답은 초안, 판단은 사람이'가 떠 있다
    ]),
}


def fetch(out, i, text):
    f = os.path.join(out, 'el', f'{i:02d}.mp3')
    if os.path.exists(f):
        return f
    key = os.environ.get('ELEVENLABS_API_KEY') or subprocess.run(  # 환경변수, 없으면 macOS 키체인(서비스 elevenlabs)
        ['security', 'find-generic-password', '-a', getpass.getuser(), '-s', 'elevenlabs', '-w'],
        capture_output=True, text=True, check=True).stdout.strip()
    req = urllib.request.Request(
        f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128',
        data=json.dumps({'text': text, 'model_id': 'eleven_v4'}).encode(),
        headers={'xi-api-key': key, 'Content-Type': 'application/json'})
    open(f, 'wb').write(urllib.request.urlopen(req).read())
    return f


def dur(path):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                capture_output=True, text=True).stdout)


if __name__ == '__main__':
    v = sys.argv[1] if len(sys.argv) > 1 else 'A'
    tempo = float(sys.argv[2]) if len(sys.argv) > 2 else 1.2
    end, cues = CUES[v]
    OUT = os.path.join(ROOT, 'audio', 'out', f'narr{v}')
    os.makedirs(os.path.join(OUT, 'el'), exist_ok=True)
    out, worst = [], 0.0
    for i, (start, sub, small, narr) in enumerate(cues, 1):
        src = fetch(OUT, i, narr)
        wav = os.path.join(OUT, f'{i:02d}.wav')
        af = ('silenceremove=start_periods=1:start_threshold=-50dB,areverse,'
              'silenceremove=start_periods=1:start_threshold=-50dB,areverse,'
              f'atempo={tempo},loudnorm=I=-18:TP=-2:LRA=7')
        subprocess.run([FF, '-v', 'error', '-y', '-i', src, '-af', af, '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', wav], check=True)
        d = round(dur(wav), 3)
        nxt = cues[i][0] if i < len(cues) else end
        room = round(nxt - start - 0.12, 3)
        worst = max(worst, d - room)
        flag = '' if d <= room else f'  ⚠ {d - room:+.2f}s 넘침'
        print(f'{i:02d} {start:5.2f}s  말 {d:4.2f}s / 자리 {room:4.2f}s{flag}  {narr}')
        out.append({'i': i, 'start': start, 'dur': d, 'sub': sub, 'small': small, 'narr': narr})
    json.dump(out, open(os.path.join(OUT, 'cues.json'), 'w'), ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, 'comp', f'narr_{v}.js'), 'w') as fh:
        fh.write(f'window.NARR_{v} = ' + json.dumps([[c['start'], c['dur'], c['sub'], c['small']] for c in out], ensure_ascii=False) + ';\n')
    print(f'{v} · 속도 {tempo} · 최대 넘침 {worst:+.2f}s')
