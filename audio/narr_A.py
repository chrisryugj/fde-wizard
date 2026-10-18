"""영상 A 나레이션: 대본(시작 초·자막·읽기) → ElevenLabs 진건 송(eleven_v4) → 다듬기
→ audio/out/narrA/NN.wav, audio/out/narrA/cues.json, comp/narr_A.js
python narr_A.py [속도(기본 1.2)]   ※ 받은 mp3 는 el/ 에 캐시 — 문장을 고치면 그 번호 mp3 를 지울 것"""
import getpass
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'audio', 'out', 'narrA')
VOICE = 'BbsagRO6ohd8MKPS2Ob0'  # 진건 송
FF = 'ffmpeg'

# (시작 초, 화면 자막, 읽을 문장) — 시작은 컷 직후 0.1~0.3초. 컷: 3.0 4.5 7.5 10.5 12.5 16.5 19.5 21.5 24.0 27.5
CUES = [
    (0.15, '광진구청 주무관을 마법사로 만들어 봤습니다', '광진구청 주무관을 마법사로 만들어 봤습니다.'),
    (3.05, '보고 만든 건 사진 한 장', '보고 만든 건, 사진 한 장.'),
    (5.08, '부품 69개를 코드로 붙였습니다', '부품 예순아홉 개를 코드로 붙였습니다.'),
    (7.65, '치수와 색은 파일 하나에 숫자로 들어 있습니다', '치수와 색은 파일 하나에 숫자로 들어 있습니다.'),
    (10.65, '뼈는 44개', '뼈는 마흔네 개.'),
    (12.65, '손발 끝만 옮기면 팔다리가 따라옵니다. 걷는 것도요', '손발 끝만 옮기면 팔다리가 따라옵니다. 걷는 것도요.'),
    (16.65, '자세는 목록에서 고르면 됩니다', '자세는 목록에서 고르면 됩니다.'),
    (19.55, '모자와 망토는 알아서 흔들리고', '모자와 망토는 알아서 흔들리고,'),
    (21.95, '인사하면 모자가 미끄러집니다', '인사하면 모자가 미끄러집니다.'),
    (24.70, '주문을 외우면 곰돌이가 나옵니다', '주문을 외우면, 곰돌이가 나옵니다.'),
    (27.65, '처음부터 끝까지, Claude Code가 쓴 Blender Python입니다', '처음부터 끝까지, 클로드 코드가 쓴 블렌더 파이썬입니다.'),
]
END = 32.0


def fetch(i, text):
    f = os.path.join(OUT, 'el', f'{i:02d}.mp3')
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
    tempo = float(sys.argv[1]) if len(sys.argv) > 1 else 1.2
    os.makedirs(os.path.join(OUT, 'el'), exist_ok=True)
    out, worst = [], 0.0
    for i, (start, sub, narr) in enumerate(CUES, 1):
        src = fetch(i, narr)
        wav = os.path.join(OUT, f'{i:02d}.wav')
        af = ('silenceremove=start_periods=1:start_threshold=-50dB,areverse,'
              'silenceremove=start_periods=1:start_threshold=-50dB,areverse,'
              f'atempo={tempo},loudnorm=I=-18:TP=-2:LRA=7')
        subprocess.run([FF, '-v', 'error', '-y', '-i', src, '-af', af, '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', wav], check=True)
        d = round(dur(wav), 3)
        nxt = CUES[i][0] if i < len(CUES) else END
        room = round(nxt - start - 0.12, 3)
        worst = max(worst, d - room)
        flag = '' if d <= room else f'  ⚠ {d - room:+.2f}s 넘침'
        print(f'{i:02d} {start:5.2f}s  말 {d:4.2f}s / 자리 {room:4.2f}s{flag}  {narr}')
        out.append({'i': i, 'start': start, 'dur': d, 'sub': sub, 'narr': narr})
    json.dump(out, open(os.path.join(OUT, 'cues.json'), 'w'), ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, 'comp', 'narr_A.js'), 'w') as fh:
        fh.write('window.NARR_A = ' + json.dumps([[c['start'], c['dur'], c['sub']] for c in out], ensure_ascii=False) + ';\n')
    print(f'속도 {tempo} · 최대 넘침 {worst:+.2f}s')
