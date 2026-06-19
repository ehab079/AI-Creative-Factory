from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import json
import os
import re
import random
import shutil
import subprocess
import time
import sys
import asyncio
import math
import wave
import struct
from datetime import datetime


# ======================================================
# AI Creative Factory - Production Pipeline Server
# Production Stable v8
# Topic Matrix + Formal Arabic + Unique Episodes
# Written Outro + Safe Original Background Music
# ======================================================

HOST = "0.0.0.0"
PORT = 8110

BASE_DIR = r"D:\AI_Creative_Factory"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
FINAL_DIR = os.path.join(BASE_DIR, "final")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
CHARACTERS_DIR = os.path.join(BASE_DIR, "characters")

PYTHON_EXE = r"C:\Users\IT SHOP\AppData\Local\Programs\Python\Python312\python.exe"

SCRIPT_FILE = os.path.join(OUTPUT_DIR, "script.txt")
TITLE_FILE = os.path.join(OUTPUT_DIR, "episode_title.txt")
METADATA_FILE = os.path.join(OUTPUT_DIR, "metadata.json")
USED_TOPICS_FILE = os.path.join(OUTPUT_DIR, "used_topics.json")

BOB_PROMPT_FILE = os.path.join(OUTPUT_DIR, "bob_image_prompt.txt")
NOVA_PROMPT_FILE = os.path.join(OUTPUT_DIR, "nova_image_prompt.txt")

BOB_CHARACTER_SOURCE = os.path.join(CHARACTERS_DIR, "bob", "lipsync_ready.png")
NOVA_CHARACTER_SOURCE = os.path.join(CHARACTERS_DIR, "nova", "lipsync_ready.png")

BOB_FINAL_IMAGE = os.path.join(FINAL_DIR, "teacher_bob_lipsync_ready.png")
NOVA_FINAL_IMAGE = os.path.join(FINAL_DIR, "nova_lipsync_ready.png")

TALKING_SCRIPT = os.path.join(TOOLS_DIR, "generate_talking_avatars.py")

# آخر فيديو فقط، يتم الكتابة فوقه كل تشغيل
FINAL_VIDEO = os.path.join(FINAL_DIR, "episode_final_talking_avatars.mp4")

# حفظ كل حلقة باسم مختلف
EPISODES_DIR = os.path.join(FINAL_DIR, "episodes")

# موسيقى أصلية محلية
MUSIC_FILE = os.path.join(FINAL_DIR, "original_background_music.wav")
MUSIC_MIXED_VIDEO = os.path.join(FINAL_DIR, "episode_final_music_mix.mp4")

# خاتمة مكتوبة
OUTRO_IMAGE = os.path.join(FINAL_DIR, "outro_card.png")
OUTRO_VIDEO = os.path.join(FINAL_DIR, "outro_card.mp4")
FINAL_WITH_OUTRO = os.path.join(FINAL_DIR, "episode_final_with_outro.mp4")
OUTRO_SECONDS = 4


# ======================================================
# Topic Matrix
# 20 domains × 10 angles = 200 ideas
# ======================================================

TOPIC_DOMAINS = [
    "الذكاء الاصطناعي في التعليم",
    "الأمن السيبراني للمبتدئين",
    "تحليل البيانات في العمل",
    "التحول الرقمي في المؤسسات",
    "البنوك الرقمية والخدمات المالية",
    "الكاميرات الذكية وأنظمة المراقبة",
    "إنترنت الأشياء في الحياة اليومية",
    "الحوسبة السحابية",
    "الروبوتات في الصناعة",
    "الصحة الرقمية",
    "التجارة الإلكترونية",
    "التسويق الرقمي",
    "المدن الذكية",
    "الطاقة المتجددة والتكنولوجيا",
    "التعلم الإلكتروني",
    "حماية الخصوصية على الإنترنت",
    "إدارة الوقت باستخدام التكنولوجيا",
    "مهارات العمل في العصر الرقمي",
    "صناعة المحتوى بالذكاء الاصطناعي",
    "ريادة الأعمال الرقمية"
]

TOPIC_ANGLES = [
    "كيف يغير {domain} مستقبل العمل؟",
    "ما أهم فوائد {domain} للمبتدئين؟",
    "ما الأخطاء الشائعة عند استخدام {domain}؟",
    "كيف نبدأ في فهم {domain} خطوة بخطوة؟",
    "ما الفرق بين الاستخدام الصحيح والخاطئ لـ {domain}؟",
    "كيف يساعد {domain} في اتخاذ قرارات أفضل؟",
    "ما علاقة {domain} بتوفير الوقت وزيادة الإنتاجية؟",
    "ما المخاطر التي يجب الانتباه لها في {domain}؟",
    "كيف تستفيد المؤسسات من {domain}؟",
    "ما المهارات المطلوبة لفهم {domain}؟"
]


# ======================================================
# Helpers
# ======================================================

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FINAL_DIR, exist_ok=True)
    os.makedirs(EPISODES_DIR, exist_ok=True)


def clean_text(text):
    return re.sub(r"\s+", " ", str(text or "").strip())


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def make_episode_id():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_filename(text, max_len=70):
    text = str(text or "").strip()
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"\s+", "_", text)
    text = text.strip("_")
    return text[:max_len] if text else "episode"


def build_topic_pool():
    topics = []

    for domain in TOPIC_DOMAINS:
        for angle in TOPIC_ANGLES:
            topics.append(angle.format(domain=domain))

    return topics


def load_used_topics():
    if not os.path.exists(USED_TOPICS_FILE):
        return []

    try:
        with open(USED_TOPICS_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

        return []

    except Exception:
        return []


def save_used_topics(used_topics):
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(used_topics, f, ensure_ascii=False, indent=2)


def pick_topic(user_topic=""):
    """
    لو المستخدم كتب topic في الرابط يتم استخدامه.
    لو لم يكتب topic يتم اختيار فكرة جديدة من مصفوفة 200 فكرة بدون تكرار.
    """
    if user_topic:
        return clean_text(user_topic)

    topic_pool = build_topic_pool()
    used_topics = load_used_topics()

    available_topics = [
        topic for topic in topic_pool
        if topic not in used_topics
    ]

    if not available_topics:
        used_topics = []
        available_topics = topic_pool

    selected_topic = random.choice(available_topics)

    used_topics.append(selected_topic)
    save_used_topics(used_topics)

    return selected_topic


# ======================================================
# 1) Build episode files
# ======================================================

def build_episode_files(topic):
    episode_id = make_episode_id()

    episode_title = f"نوفا وبوب يشرحان\n{topic}"

    # فصحى بسيطة، بدون نطق جملة اللايك والمتابعة
    # 10 أسطر بالضبط
    script = f"""
بوب: مرحبًا بكم في حلقة تعليمية جديدة من نوفا والمعلم بوب.
نوفا: أهلًا بكم، موضوع اليوم هو: {topic}
بوب: دعينا نبدأ من السؤال الأساسي: لماذا هذا الموضوع مهم في وقتنا الحالي؟
نوفا: لأنه يساعدنا على فهم التغيرات من حولنا، واستخدام التكنولوجيا بطريقة أكثر وعيًا.
بوب: وما أول فكرة يجب أن ينتبه إليها المشاهد؟
نوفا: أن القيمة لا تأتي من الأداة وحدها، بل من طريقة استخدامها في حل مشكلة حقيقية.
بوب: وهل يحتاج فهم هذا الموضوع إلى خبرة كبيرة من البداية؟
نوفا: لا، البداية الصحيحة تكون بفهم المفهوم، ثم تجربة خطوات بسيطة، ثم تطوير المهارة تدريجيًا.
بوب: إذن النجاح يعتمد على الفهم والتنظيم، وليس على استخدام الأدوات بشكل عشوائي.
نوفا: بالضبط، ومع التعلم المستمر تتحول المعرفة إلى فرصة حقيقية في الدراسة والعمل والحياة.
""".strip()

    metadata = {
        "project": "AI Creative Factory",
        "mode": "production_stable_v8_written_outro_safe_music",
        "episode_id": episode_id,
        "topic": topic,
        "episode_title": episode_title,
        "language_style": "Simple Formal Arabic",
        "characters_source": "Character Library",
        "created_at": datetime.now().isoformat(),
        "topic_generation": {
            "method": "matrix",
            "domains_count": len(TOPIC_DOMAINS),
            "angles_count": len(TOPIC_ANGLES),
            "total_possible_topics": len(TOPIC_DOMAINS) * len(TOPIC_ANGLES),
            "used_topics_file": USED_TOPICS_FILE
        },
        "outro_text": "من فضلك ادعم القناة واعمل مشاركة ولايك وتابعنا لمتابعة كل جديد",
        "background_music": {
            "type": "generated_original_music",
            "music_file": MUSIC_FILE,
            "safe_mix": True
        },
        "pipeline": [
            "build_episode_files",
            "script_quality_guard",
            "sync_character_library",
            "generate_voice",
            "generate_talking_avatars",
            "create_final_video",
            "mix_original_music_into_final_video",
            "append_outro_to_final_video",
            "save_unique_episode_video"
        ]
    }

    bob_prompt = "Bob character is loaded from Character Library. Image generation disabled in production mode."
    nova_prompt = "Nova character is loaded from Character Library. Image generation disabled in production mode."

    write_text(SCRIPT_FILE, script)
    write_text(TITLE_FILE, episode_title)
    write_text(BOB_PROMPT_FILE, bob_prompt)
    write_text(NOVA_PROMPT_FILE, nova_prompt)
    write_text(METADATA_FILE, json.dumps(metadata, ensure_ascii=False, indent=2))

    return {
        "episode_id": episode_id,
        "topic": topic,
        "episode_title": episode_title,
        "script_file": SCRIPT_FILE,
        "metadata_file": METADATA_FILE
    }


# ======================================================
# 2) Script quality guard
# ======================================================

def validate_script():
    if not os.path.exists(SCRIPT_FILE):
        raise FileNotFoundError(f"script.txt not found: {SCRIPT_FILE}")

    with open(SCRIPT_FILE, "r", encoding="utf-8-sig") as f:
        text = f.read().strip()

    lines = [clean_text(x) for x in text.splitlines() if clean_text(x)]

    errors = []
    warnings = []

    if len(lines) != 10:
        errors.append(f"Expected exactly 10 dialogue lines, found {len(lines)}.")

    expected = ["بوب", "نوفا"] * 5

    for i, line in enumerate(lines):
        match = re.match(r"^(بوب|نوفا)\s*[:：]\s*(.+)$", line)

        if not match:
            errors.append(f"Line {i + 1} must start with بوب: or نوفا:")
            continue

        speaker = match.group(1)
        speech = match.group(2).strip()

        if i < len(expected) and speaker != expected[i]:
            errors.append(f"Line {i + 1} speaker should be {expected[i]}, found {speaker}.")

        if len(speech) > 220:
            warnings.append(f"Line {i + 1} is long and may slow voice timing.")

    if errors:
        raise RuntimeError("Script validation failed: " + " | ".join(errors))

    return {
        "ok": True,
        "lines_count": len(lines),
        "warnings": warnings
    }


# ======================================================
# 3) Character library sync
# ======================================================

def sync_character_library():
    missing = []

    if not os.path.exists(BOB_CHARACTER_SOURCE):
        missing.append(BOB_CHARACTER_SOURCE)

    if not os.path.exists(NOVA_CHARACTER_SOURCE):
        missing.append(NOVA_CHARACTER_SOURCE)

    if missing:
        raise FileNotFoundError("Missing character images: " + json.dumps(missing, ensure_ascii=False))

    shutil.copy2(BOB_CHARACTER_SOURCE, BOB_FINAL_IMAGE)
    shutil.copy2(NOVA_CHARACTER_SOURCE, NOVA_FINAL_IMAGE)

    return {
        "bob": BOB_FINAL_IMAGE,
        "nova": NOVA_FINAL_IMAGE
    }


# ======================================================
# 4) Voice generation
# ======================================================

def generate_voice():
    sys.path.insert(0, TOOLS_DIR)

    import voice_bridge

    with open(SCRIPT_FILE, "r", encoding="utf-8-sig") as f:
        script = f.read().strip()

    dialogue = voice_bridge.parse_dialogue_script(script)
    total_duration, timing = asyncio.run(voice_bridge.generate_dialogue_voice(dialogue))

    return {
        "duration_seconds": round(total_duration, 2),
        "parts_count": len(timing),
        "voice_output": voice_bridge.VOICE_OUTPUT,
        "timing_json": voice_bridge.VOICE_TIMING_JSON
    }


# ======================================================
# 5) Talking avatars
# ======================================================

def run_subprocess(cmd, cwd=None, timeout=None):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(cmd)
            + "\n\nSTDOUT:\n"
            + result.stdout[-3000:]
            + "\n\nSTDERR:\n"
            + result.stderr[-6000:]
        )

    return {
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:]
    }


def generate_talking_avatars():
    if not os.path.exists(TALKING_SCRIPT):
        raise FileNotFoundError(f"generate_talking_avatars.py not found: {TALKING_SCRIPT}")

    result = run_subprocess(
        [PYTHON_EXE, TALKING_SCRIPT],
        cwd=TOOLS_DIR,
        timeout=1800
    )

    talking_dir = os.path.join(FINAL_DIR, "talking_parts")
    files = []

    if os.path.exists(talking_dir):
        files = sorted([f for f in os.listdir(talking_dir) if f.lower().endswith(".mp4")])

    if len(files) == 0:
        raise RuntimeError("No talking avatar videos were created.")

    return {
        "talking_parts_folder": talking_dir,
        "files_count": len(files),
        "files": files,
        "process": result
    }


# ======================================================
# 6) Final video creation
# ======================================================

def create_final_video():
    sys.path.insert(0, TOOLS_DIR)

    import ffmpeg_bridge

    result = ffmpeg_bridge.build_final_talking_video()

    if not os.path.exists(FINAL_VIDEO):
        raise RuntimeError(f"Final video was not created: {FINAL_VIDEO}")

    return {
        "output": FINAL_VIDEO,
        "details": result
    }


# ======================================================
# 7) Original background music
# ======================================================

def create_original_background_music():
    """
    توليد موسيقى أصلية بسيطة محليًا بدون استخدام أي ملف خارجي.
    """
    sample_rate = 44100
    duration_seconds = 20
    amplitude = 5000

    melody_notes = [
        261.63, 329.63, 392.00, 523.25,
        392.00, 329.63, 293.66, 349.23
    ]

    bass_notes = [
        130.81, 146.83, 164.81, 196.00
    ]

    beat_seconds = 0.5
    total_samples = int(sample_rate * duration_seconds)

    os.makedirs(FINAL_DIR, exist_ok=True)

    with wave.open(MUSIC_FILE, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        for i in range(total_samples):
            t = i / sample_rate

            melody_index = int(t / beat_seconds) % len(melody_notes)
            bass_index = int(t / 2.0) % len(bass_notes)

            melody = melody_notes[melody_index]
            bass = bass_notes[bass_index]

            beat_pos = (t % beat_seconds) / beat_seconds
            envelope = min(beat_pos * 8, 1.0, (1 - beat_pos) * 8)

            value = (
                0.55 * math.sin(2 * math.pi * melody * t) +
                0.25 * math.sin(2 * math.pi * melody * 1.5 * t) +
                0.20 * math.sin(2 * math.pi * bass * t)
            )

            sample = int(amplitude * envelope * value)
            sample = max(-32767, min(32767, sample))

            wav.writeframes(struct.pack("<h", sample))

    return MUSIC_FILE


def mix_original_music_into_final_video():
    """
    دمج آمن للموسيقى:
    - يحافظ على صوت الكلام الأصلي
    - يضيف الموسيقى بمستوى منخفض جدًا
    - لو فشل الدمج لا يحذف الفيديو الأصلي
    """
    if not os.path.exists(FINAL_VIDEO):
        raise RuntimeError(f"Final video not found: {FINAL_VIDEO}")

    create_original_background_music()

    if os.path.exists(MUSIC_MIXED_VIDEO):
        os.remove(MUSIC_MIXED_VIDEO)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", FINAL_VIDEO,
        "-stream_loop", "-1",
        "-i", MUSIC_FILE,
        "-filter_complex",
        "[0:a]volume=1.0[a_voice];[1:a]volume=0.04[a_music];[a_voice][a_music]amix=inputs=2:duration=first:dropout_transition=2[a_out]",
        "-map", "0:v:0",
        "-map", "[a_out]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        MUSIC_MIXED_VIDEO
    ]

    try:
        run_subprocess(cmd, cwd=FINAL_DIR, timeout=300)

        if not os.path.exists(MUSIC_MIXED_VIDEO):
            raise RuntimeError("Music mixed video was not created.")

        backup_original = os.path.join(FINAL_DIR, "episode_final_before_music_backup.mp4")

        if os.path.exists(backup_original):
            os.remove(backup_original)

        shutil.copy2(FINAL_VIDEO, backup_original)

        os.remove(FINAL_VIDEO)
        shutil.move(MUSIC_MIXED_VIDEO, FINAL_VIDEO)

        return {
            "music_file": MUSIC_FILE,
            "mixed_video": FINAL_VIDEO,
            "music_status": "Original background music mixed successfully",
            "music_volume": "0.04",
            "backup_original": backup_original
        }

    except Exception as e:
        return {
            "music_file": MUSIC_FILE,
            "mixed_video": FINAL_VIDEO,
            "music_status": "Music mix failed; original video kept unchanged",
            "error": str(e)
        }


# ======================================================
# 8) Written outro card
# ======================================================

def shape_arabic_text(text):
    """
    تجهيز النص العربي للعرض الصحيح داخل صورة الخاتمة.
    يحتاج arabic-reshaper و python-bidi.
    لو غير موجودين، يعرض النص كما هو.
    """
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)

    except Exception:
        return text


def create_outro_card():
    """
    إنشاء صورة خاتمة مكتوبة.
    جملة الدعم هنا مكتوبة فقط وليست منطوقة.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        raise RuntimeError(
            "Pillow is required for outro card. Install it with: "
            f"{PYTHON_EXE} -m pip install pillow arabic-reshaper python-bidi"
        )

    width, height = 1080, 1920

    img = Image.new("RGB", (width, height), (8, 18, 38))
    draw = ImageDraw.Draw(img)

    font_paths = [
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf"
    ]

    font_big = None
    font_small = None

    for fp in font_paths:
        if os.path.exists(fp):
            font_big = ImageFont.truetype(fp, 66)
            font_small = ImageFont.truetype(fp, 44)
            break

    if font_big is None:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # خلفية بسيطة فيها خطوط ضوئية
    for y in range(0, height, 80):
        shade = int(20 + (y / height) * 35)
        draw.line((0, y, width, y), fill=(shade, shade + 20, shade + 45), width=2)

    # إطار
    draw.rounded_rectangle(
        (80, 560, 1000, 1240),
        radius=40,
        outline=(90, 190, 255),
        width=5,
        fill=(10, 28, 58)
    )

    lines = [
        "من فضلك ادعم القناة",
        "واعمل مشاركة ولايك",
        "وتابعنا لمتابعة كل جديد"
    ]

    y = 710

    for line in lines:
        display_line = shape_arabic_text(line)
        bbox = draw.textbbox((0, 0), display_line, font=font_big)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2

        draw.text((x + 3, y + 3), display_line, font=font_big, fill=(0, 0, 0))
        draw.text((x, y), display_line, font=font_big, fill=(255, 255, 255))

        y += 115

    sub = shape_arabic_text("نوفا والمعلم بوب")
    bbox = draw.textbbox((0, 0), sub, font=font_small)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w) // 2, 1120), sub, font=font_small, fill=(120, 210, 255))

    img.save(OUTRO_IMAGE)
    return OUTRO_IMAGE


def create_outro_video():
    create_outro_card()

    if os.path.exists(OUTRO_VIDEO):
        os.remove(OUTRO_VIDEO)

    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", OUTRO_IMAGE,
        "-f", "lavfi",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t", str(OUTRO_SECONDS),
        "-vf", "scale=1080:1920,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        OUTRO_VIDEO
    ]

    run_subprocess(cmd, cwd=FINAL_DIR, timeout=120)

    if not os.path.exists(OUTRO_VIDEO):
        raise RuntimeError("Outro video was not created.")

    return OUTRO_VIDEO


def append_outro_to_final_video():
    """
    إضافة خاتمة مكتوبة في آخر الفيديو.
    """
    if not os.path.exists(FINAL_VIDEO):
        raise RuntimeError(f"Final video not found: {FINAL_VIDEO}")

    create_outro_video()

    concat_file = os.path.join(FINAL_DIR, "concat_outro_list.txt")

    with open(concat_file, "w", encoding="utf-8") as f:
        f.write(f"file '{FINAL_VIDEO.replace(os.sep, '/')}'\n")
        f.write(f"file '{OUTRO_VIDEO.replace(os.sep, '/')}'\n")

    if os.path.exists(FINAL_WITH_OUTRO):
        os.remove(FINAL_WITH_OUTRO)

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        FINAL_WITH_OUTRO
    ]

    run_subprocess(cmd, cwd=FINAL_DIR, timeout=300)

    if not os.path.exists(FINAL_WITH_OUTRO):
        raise RuntimeError("Final video with outro was not created.")

    os.remove(FINAL_VIDEO)
    shutil.move(FINAL_WITH_OUTRO, FINAL_VIDEO)

    return {
        "outro_image": OUTRO_IMAGE,
        "outro_video": OUTRO_VIDEO,
        "final_video_with_outro": FINAL_VIDEO,
        "outro_seconds": OUTRO_SECONDS,
        "outro_text": "من فضلك ادعم القناة واعمل مشاركة ولايك وتابعنا لمتابعة كل جديد"
    }


# ======================================================
# 9) Save unique copy for every episode
# ======================================================

def save_unique_episode_video(episode_id, topic):
    if not os.path.exists(FINAL_VIDEO):
        raise RuntimeError(f"Final video not found: {FINAL_VIDEO}")

    os.makedirs(EPISODES_DIR, exist_ok=True)

    safe_topic = safe_filename(topic)
    unique_name = f"{episode_id}_{safe_topic}.mp4"
    unique_path = os.path.join(EPISODES_DIR, unique_name)

    shutil.copy2(FINAL_VIDEO, unique_path)

    return {
        "unique_video_path": unique_path,
        "unique_video_name": unique_name,
        "latest_video_path": FINAL_VIDEO,
        "episodes_folder": EPISODES_DIR
    }


# ======================================================
# Main production pipeline
# ======================================================

def produce_episode(topic=""):
    ensure_dirs()

    start = time.time()
    selected_topic = pick_topic(topic)

    step_results = {}

    step_results["episode_files"] = build_episode_files(selected_topic)
    step_results["script_quality"] = validate_script()
    step_results["character_sync"] = sync_character_library()
    step_results["voice"] = generate_voice()
    step_results["talking_avatars"] = generate_talking_avatars()
    step_results["final_video"] = create_final_video()

    # دمج الموسيقى بشكل آمن
    step_results["background_music"] = mix_original_music_into_final_video()

    # إضافة خاتمة مكتوبة بدل نطق جملة اللايك والمتابعة
    step_results["outro"] = append_outro_to_final_video()

    # الأرشفة بعد الموسيقى والخاتمة
    step_results["episode_archive"] = save_unique_episode_video(
        step_results["episode_files"]["episode_id"],
        selected_topic
    )

    duration = round(time.time() - start, 2)

    return {
        "ok": True,
        "message": "Production episode completed successfully",
        "duration_seconds": duration,
        "topic": selected_topic,
        "final_video": step_results["episode_archive"]["unique_video_path"],
        "latest_video": FINAL_VIDEO,
        "steps": step_results
    }


# ======================================================
# HTTP Server
# ======================================================

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self.send_json(200, {
                "ok": True,
                "message": "Production Pipeline Server is running",
                "port": PORT,
                "version": "Production Stable v8 - Written Outro + Safe Original Music",
                "topics_count": len(TOPIC_DOMAINS) * len(TOPIC_ANGLES),
                "used_topics_file": USED_TOPICS_FILE,
                "episodes_dir": EPISODES_DIR
            })
            return

        if parsed.path != "/produce-episode":
            self.send_json(404, {
                "ok": False,
                "error": "Use /health or /produce-episode"
            })
            return

        query = parse_qs(parsed.query)
        topic = clean_text(query.get("topic", [""])[0])

        try:
            result = produce_episode(topic)
            self.send_json(200, result)

        except Exception as e:
            self.send_json(500, {
                "ok": False,
                "error": str(e),
                "final_video": FINAL_VIDEO
            })


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)

    print("=" * 80)
    print("AI Creative Factory - Production Pipeline Server")
    print("Production Stable v8")
    print("Topic Matrix + Formal Arabic + Unique Episodes")
    print("Written Outro + Safe Original Background Music")
    print("=" * 80)
    print(f"Running on: http://127.0.0.1:{PORT}")
    print("Health:")
    print(f"http://127.0.0.1:{PORT}/health")
    print("Endpoint:")
    print(f"http://127.0.0.1:{PORT}/produce-episode")
    print("Example:")
    print(f"http://127.0.0.1:{PORT}/produce-episode?topic=الكاميرات الذكية وأنظمة المراقبة")
    print("=" * 80)

    server.serve_forever()