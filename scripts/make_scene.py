"""직접 만져 보는 장면 파일: 스튜디오 + 포즈 에셋(포즈 라이브러리) → out/fde_wizard_scene.blend
blender -b build/rig.blend -P make_scene.py"""
import sys
import os
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poses  # noqa: E402
import shots_common as SC  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL = {'rest': '기본', 'idle': '대기', 'wave': '손인사', 'bow': '인사', 'cast': '주문', 'thumbs': '엄지척', 'tada': '짠', 'think': '생각'}

cam, L, cyc = SC.studio(lens=50, samples=32)
SC.cam_full(cam, 1, -18, 5)
SC.hide_bear(False)
SC.bear_root().location = (0.85, -0.2, 1.25)
rig = bpy.data.objects['rig']
rig.animation_data_create()
made = []
for name in ('rest', 'idle', 'wave', 'bow', 'cast', 'thumbs', 'tada', 'think'):
    act = bpy.data.actions.new(f'포즈 · {LABEL[name]}')
    rig.animation_data.action = act
    poses.apply(rig, name)
    for n, path in poses.CHANNELS:
        rig.pose.bones[n].keyframe_insert(path, frame=1)
    act.use_fake_user = True
    act.asset_mark()
    made.append(act.name)
rig.animation_data.action = None
poses.apply(rig, 'idle')
for o in SC.viz_objects():
    o.hide_render = True
    o.hide_viewport = True
bpy.context.scene.frame_set(1)
out = os.path.join(ROOT, 'out', 'fde_wizard_scene.blend')
if os.environ.get('RELEASE'):
    # 공개용: 공무원증을 자리표시 텍스처로 바꿔 파일 안에 넣고, 내 컴퓨터 경로·화면 설정은 남기지 않는다
    img = bpy.data.images.get('card.png')
    if img:
        img.filepath = bpy.path.relpath(os.path.join(ROOT, 'build', 'tex', 'card_placeholder.png'))  # 상대경로로 바꾼 뒤 팩
        img.reload()
        img.pack()
        for pf in img.packed_files:  # 팩 기록에는 절대경로가 따로 남는다 — 이것도 상대경로로
            pf.filepath = img.filepath
    builtin = bpy.data.fonts.load('<builtin>')  # 재배포하지 않는 폰트는 빼고 블렌더 기본 글꼴로(라벨은 HWP·PDF 라틴 문자뿐)
    for cu in bpy.data.curves:
        if getattr(cu, 'font', None) is not None:
            cu.font = cu.font_bold = cu.font_italic = cu.font_bold_italic = builtin
    for f in list(bpy.data.fonts):
        if f is not builtin:
            bpy.data.fonts.remove(f, do_unlink=True)
    out = os.path.join(ROOT, 'assets', 'fde_wizard_scene.blend')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # 화면(UI) 없이 데이터블록만 쓴다 — 파일 브라우저가 기억하는 홈 폴더 경로가 안 들어간다
    blocks = {bpy.context.scene} | {a for a in bpy.data.actions if a.asset_data}
    bpy.data.libraries.write(out, blocks, path_remap='RELATIVE_ALL', compress=True)
else:
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
print('SCENE_SAVED', made)
