#!/usr/bin/env python3
# assets/generate_gifs.py
# -----------------------------------------------------------------
# Pillow로 상태별 픽셀아트 GIF 애니메이션을 생성한다.
# 각 상태별 120x120px, 8fps, 무한 루프
# -----------------------------------------------------------------

import os
import math
from PIL import Image, ImageDraw

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gif')
SIZE = 120
FPS = 8
FRAME_DURATION = 1000 // FPS  # ms per frame
FRAMES = 8

# 크랩 펫 색상
CRAB_BODY = (255, 107, 107)       # 빨간색 몸
CRAB_DARK = (200, 60, 60)         # 어두운 빨간
CRAB_EYE_WHITE = (255, 255, 255)
CRAB_EYE_BLACK = (30, 30, 30)
CRAB_CLAW = (255, 140, 100)
BG = (0, 0, 0, 0)  # 투명 배경


def draw_crab(draw, cx, cy, scale=1.0, eye_offset_x=0, claw_angle=0, blush=False):
    """간단한 픽셀 크랩을 그린다."""
    s = scale
    # 몸통 (타원)
    body_w, body_h = int(28 * s), int(20 * s)
    draw.ellipse(
        [cx - body_w, cy - body_h, cx + body_w, cy + body_h],
        fill=CRAB_BODY, outline=CRAB_DARK, width=2
    )

    # 눈 (좌)
    ew = int(8 * s)
    ex_l = cx - int(14 * s) + eye_offset_x
    ey = cy - int(8 * s)
    draw.ellipse([ex_l - ew, ey - ew, ex_l + ew, ey + ew], fill=CRAB_EYE_WHITE)
    draw.ellipse([ex_l - 3 + eye_offset_x, ey - 3, ex_l + 3 + eye_offset_x, ey + 3], fill=CRAB_EYE_BLACK)

    # 눈 (우)
    ex_r = cx + int(14 * s) + eye_offset_x
    draw.ellipse([ex_r - ew, ey - ew, ex_r + ew, ey + ew], fill=CRAB_EYE_WHITE)
    draw.ellipse([ex_r - 3 + eye_offset_x, ey - 3, ex_r + 3 + eye_offset_x, ey + 3], fill=CRAB_EYE_BLACK)

    # 집게 (좌)
    cl_x = cx - int(32 * s)
    cl_y = cy + int(claw_angle * 3)
    draw.ellipse([cl_x - 8, cl_y - 10, cl_x + 8, cl_y + 10], fill=CRAB_CLAW, outline=CRAB_DARK)

    # 집게 (우)
    cr_x = cx + int(32 * s)
    cr_y = cy - int(claw_angle * 3)
    draw.ellipse([cr_x - 8, cr_y - 10, cr_x + 8, cr_y + 10], fill=CRAB_CLAW, outline=CRAB_DARK)

    # 다리 (4쌍)
    for i in range(4):
        leg_y = cy + int(12 * s) + i * int(5 * s)
        leg_len = int(12 * s)
        draw.line([(cx - body_w, leg_y), (cx - body_w - leg_len, leg_y + 4)], fill=CRAB_DARK, width=2)
        draw.line([(cx + body_w, leg_y), (cx + body_w + leg_len, leg_y + 4)], fill=CRAB_DARK, width=2)

    # 볼 빨개짐
    if blush:
        draw.ellipse([cx - 24, cy + 2, cx - 14, cy + 10], fill=(255, 180, 180))
        draw.ellipse([cx + 14, cy + 2, cx + 24, cy + 10], fill=(255, 180, 180))


def generate_idle():
    """idle: 좌우로 부드럽게 흔들림."""
    frames = []
    for i in range(FRAMES):
        img = Image.new('RGBA', (SIZE, SIZE), BG)
        draw = ImageDraw.Draw(img)
        offset_y = math.sin(i / FRAMES * math.pi * 2) * 3
        draw_crab(draw, SIZE // 2, SIZE // 2 + int(offset_y), eye_offset_x=0)
        frames.append(img)
    return frames


def generate_thinking():
    """thinking: 눈이 위를 보며 좌우로 움직임."""
    frames = []
    for i in range(FRAMES):
        img = Image.new('RGBA', (SIZE, SIZE), BG)
        draw = ImageDraw.Draw(img)
        eye_x = int(math.sin(i / FRAMES * math.pi * 2) * 3)
        draw_crab(draw, SIZE // 2, SIZE // 2, eye_offset_x=eye_x)
        # 물음표
        if i % 2 == 0:
            draw.text((SIZE // 2 + 25, SIZE // 2 - 35), "?", fill=(100, 100, 100))
        frames.append(img)
    return frames


def generate_working():
    """working: 집게가 위아래로 빠르게 움직임."""
    frames = []
    for i in range(FRAMES):
        img = Image.new('RGBA', (SIZE, SIZE), BG)
        draw = ImageDraw.Draw(img)
        claw = math.sin(i / FRAMES * math.pi * 4) * 3
        draw_crab(draw, SIZE // 2, SIZE // 2, claw_angle=claw)
        # 번개 이펙트
        if i in (1, 5):
            draw.text((SIZE // 2 - 5, SIZE // 2 - 40), "⚡", fill=(255, 200, 0))
        frames.append(img)
    return frames


def generate_sleeping():
    """sleeping: 눈 감고 Zzz."""
    frames = []
    for i in range(FRAMES):
        img = Image.new('RGBA', (SIZE, SIZE), BG)
        draw = ImageDraw.Draw(img)
        body_y = SIZE // 2 + 5

        # 몸통
        draw.ellipse([SIZE // 2 - 28, body_y - 18, SIZE // 2 + 28, body_y + 18],
                     fill=CRAB_BODY, outline=CRAB_DARK, width=2)

        # 감은 눈 (가로선)
        ey = body_y - 8
        draw.line([(SIZE // 2 - 20, ey), (SIZE // 2 - 8, ey)], fill=CRAB_EYE_BLACK, width=2)
        draw.line([(SIZE // 2 + 8, ey), (SIZE // 2 + 20, ey)], fill=CRAB_EYE_BLACK, width=2)

        # Zzz
        z_y = body_y - 30 - (i % 4) * 3
        draw.text((SIZE // 2 + 20, z_y), "z", fill=(150, 150, 200))
        if i >= 3:
            draw.text((SIZE // 2 + 28, z_y - 10), "z", fill=(120, 120, 180))

        # 다리
        for j in range(4):
            leg_y = body_y + 12 + j * 5
            draw.line([(SIZE // 2 - 28, leg_y), (SIZE // 2 - 40, leg_y + 4)], fill=CRAB_DARK, width=2)
            draw.line([(SIZE // 2 + 28, leg_y), (SIZE // 2 + 40, leg_y + 4)], fill=CRAB_DARK, width=2)

        frames.append(img)
    return frames


def generate_error():
    """error: 빨갛게 깜빡 + 느낌표."""
    frames = []
    for i in range(FRAMES):
        img = Image.new('RGBA', (SIZE, SIZE), BG)
        draw = ImageDraw.Draw(img)
        flash = i % 2 == 0
        draw_crab(draw, SIZE // 2, SIZE // 2)
        if flash:
            # 빨간 오버레이
            draw.ellipse([SIZE // 2 - 30, SIZE // 2 - 22, SIZE // 2 + 30, SIZE // 2 + 22],
                         fill=(255, 50, 50, 80))
        draw.text((SIZE // 2 - 2, SIZE // 2 - 42), "!", fill=(255, 50, 50))
        frames.append(img)
    return frames


def generate_happy():
    """happy: 점프 + 볼 빨개짐."""
    frames = []
    for i in range(FRAMES):
        img = Image.new('RGBA', (SIZE, SIZE), BG)
        draw = ImageDraw.Draw(img)
        jump = -abs(math.sin(i / FRAMES * math.pi)) * 15
        draw_crab(draw, SIZE // 2, SIZE // 2 + int(jump), blush=True, claw_angle=2)
        # 별 이펙트
        if i in (2, 3, 4):
            draw.text((SIZE // 2 + 30, SIZE // 2 - 30 + int(jump)), "★", fill=(255, 215, 0))
        frames.append(img)
    return frames


def generate_juggling():
    """juggling: 3개의 공을 저글링."""
    frames = []
    for i in range(FRAMES):
        img = Image.new('RGBA', (SIZE, SIZE), BG)
        draw = ImageDraw.Draw(img)
        draw_crab(draw, SIZE // 2, SIZE // 2 + 5, claw_angle=math.sin(i / FRAMES * math.pi * 2) * 2)

        # 저글링 공 3개 (원형 궤도)
        for j in range(3):
            angle = (i / FRAMES * math.pi * 2) + (j * math.pi * 2 / 3)
            bx = SIZE // 2 + int(math.cos(angle) * 20)
            by = SIZE // 2 - 25 + int(math.sin(angle) * 8)
            colors = [(100, 200, 255), (255, 200, 100), (200, 255, 100)]
            draw.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill=colors[j])

        frames.append(img)
    return frames


def generate_sweeping():
    """sweeping: 빗자루로 쓸기."""
    frames = []
    for i in range(FRAMES):
        img = Image.new('RGBA', (SIZE, SIZE), BG)
        draw = ImageDraw.Draw(img)
        sweep_x = int(math.sin(i / FRAMES * math.pi * 2) * 8)
        draw_crab(draw, SIZE // 2 + sweep_x, SIZE // 2)

        # 빗자루
        broom_x = SIZE // 2 + 35 + sweep_x
        draw.line([(broom_x, SIZE // 2 - 10), (broom_x, SIZE // 2 + 20)],
                  fill=(139, 90, 43), width=3)
        draw.polygon([(broom_x - 6, SIZE // 2 + 20), (broom_x + 6, SIZE // 2 + 20),
                      (broom_x + 4, SIZE // 2 + 30), (broom_x - 4, SIZE // 2 + 30)],
                     fill=(180, 140, 80))

        # 먼지 파티클
        if i in (2, 3, 6, 7):
            for dx, dy in [(-15, 25), (-8, 28), (-20, 22)]:
                draw.ellipse([broom_x + dx, SIZE // 2 + dy, broom_x + dx + 3, SIZE // 2 + dy + 3],
                             fill=(200, 200, 200, 150))

        frames.append(img)
    return frames


def save_gif(frames, name):
    """프레임 리스트를 GIF로 저장."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f'{name}.gif')
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_DURATION,
        loop=0,
        disposal=2,
        transparency=0,
    )
    size_kb = os.path.getsize(path) / 1024
    print(f"  ✓ {name}.gif ({size_kb:.1f}KB, {len(frames)} frames)")


def main():
    print("🦀 GIF 에셋 생성 중...\n")

    generators = {
        'idle': generate_idle,
        'thinking': generate_thinking,
        'working': generate_working,
        'sleeping': generate_sleeping,
        'error': generate_error,
        'happy': generate_happy,
        'juggling': generate_juggling,
        'sweeping': generate_sweeping,
    }

    for name, gen_func in generators.items():
        frames = gen_func()
        save_gif(frames, name)

    print(f"\n✅ {len(generators)}개 GIF 생성 완료 → {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
