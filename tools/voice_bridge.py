from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import re
import asyncio
import subprocess
import shutil
import edge_tts

HOST = "0.0.0.0"
PORT = 8100

BASE_DIR = r"D:\AI_Creative_Factory"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
FINAL_DIR = os.path.join(BASE_DIR, "final")
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPT_FILE = os.path.join(OUTPUT_DIR, "script.txt")
VOICE_OUTPUT = os.path.join(FINAL_DIR, "episode_voice.mp3")
VOICE_TIMING_JSON = os.path.join(FINAL_DIR, "episode_voice_timing.json")
TEMP_AUDIO_DIR = os.path.join(FINAL_DIR, "voice_parts")

BOB_VOICE = "ar-EG-ShakirNeural"
NOVA_VOICE = "ar-EG-SalmaNeural"


def read_text_file(path, fallback=""):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                text = f.read().strip()
                return text if text else fallback
    except Exception:
        pass
    return fallback


def clean_text(text):
    text = text.replace("\r", " ").strip()
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def normalize_speaker(speaker):
    speaker = speaker.strip().lower()

    bob_names = [
        "bob", "بوب", "المعلم بوب", "معلم بوب", "teacher bob", "teacher_bob"
    ]

    nova_names = [
        "nova", "نوفا"
    ]

    if speaker in bob_names:
        return "bob"

    if speaker in nova_names:
        return "nova"

    return ""


def parse_dialogue_script(script):
    lines = script.splitlines()
    dialogue = []

    for line in lines:
        line = clean_text(line)

        if not line:
            continue

        match = re.match(r"^(.{1,30}?)[\:\：\-–]\s*(.+)$", line)

        if match:
            speaker_raw = clean_text(match.group(1))
            text = clean_text(match.group(2))
            speaker = normalize_speaker(speaker_raw)

            if speaker and text:
                dialogue.append({
                    "speaker": speaker,
                    "text": text
                })
                continue

        # لو السطر بدون اسم متحدث، نخليه لبوب افتراضيًا
        dialogue.append({
            "speaker": "bob",
            "text": line
        })

    # لو الملف فقير جدًا أو غير مقسم، نستخدم سكريبت افتراضي
    if not dialogue:
        dialogue = [
            {
                "speaker": "bob",
                "text": "مرحبًا بكم في حلقة تعليمية جديدة من مشروع نوفا والمعلم بوب."
            },
            {
                "speaker": "nova",
                "text": "أهلًا بكم، في هذه الحلقة سنشرح الفكرة بطريقة بسيطة وسريعة."
            }
        ]

    return dialogue


async def generate_part(text, output_path, voice):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="+0%",
        volume="+0%"
    )
    await communicate.save(output_path)


def get_audio_duration_seconds(path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        return 0.0

    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def concat_audio_files(audio_files, output_path):
    concat_file = os.path.join(TEMP_AUDIO_DIR, "concat_list.txt")

    with open(concat_file, "w", encoding="utf-8") as f:
        for audio_file in audio_files:
            safe_path = audio_file.replace("\\", "/")
            f.write(f"file '{safe_path}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path
    ]

    result = subprocess.run(
        cmd,
        cwd=TOOLS_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr[-4000:])


async def generate_dialogue_voice(dialogue):
    if os.path.exists(TEMP_AUDIO_DIR):
        shutil.rmtree(TEMP_AUDIO_DIR)

    os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)
    os.makedirs(FINAL_DIR, exist_ok=True)

    audio_files = []
    timing = []
    current_time = 0.0

    for index, item in enumerate(dialogue, start=1):
        speaker = item["speaker"]
        text = item["text"]

        voice = BOB_VOICE if speaker == "bob" else NOVA_VOICE
        filename = f"{index:03d}_{speaker}.mp3"
        part_path = os.path.join(TEMP_AUDIO_DIR, filename)

        await generate_part(text, part_path, voice)

        duration = get_audio_duration_seconds(part_path)

        timing.append({
            "index": index,
            "speaker": speaker,
            "voice": voice,
            "text": text,
            "audio_file": part_path,
            "start": round(current_time, 2),
            "end": round(current_time + duration, 2),
            "duration": round(duration, 2)
        })

        current_time += duration
        audio_files.append(part_path)

    concat_audio_files(audio_files, VOICE_OUTPUT)

    total_duration = get_audio_duration_seconds(VOICE_OUTPUT)

    with open(VOICE_TIMING_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "total_duration": round(total_duration, 2),
            "output": VOICE_OUTPUT,
            "parts": timing
        }, f, ensure_ascii=False, indent=2)

    return total_duration, timing


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/generate-voice":
            self.send_json(404, {
                "ok": False,
                "error": "Use /generate-voice"
            })
            return

        script = read_text_file(
            SCRIPT_FILE,
            """بوب: مرحبًا بكم في حلقة تعليمية جديدة من مشروع نوفا والمعلم بوب.
نوفا: أهلًا بكم، اليوم سنقدم فكرة بسيطة ومفيدة بطريقة سريعة.
بوب: ما أهمية تنظيم العمل عند صناعة المحتوى بالذكاء الاصطناعي؟
نوفا: التنظيم يجعل النتيجة أوضح، ويقلل الأخطاء، ويساعدنا على إنتاج فيديو مناسب للنشر."""
        )

        dialogue = parse_dialogue_script(script)

        try:
            total_duration, timing = asyncio.run(generate_dialogue_voice(dialogue))

            if not os.path.exists(VOICE_OUTPUT):
                self.send_json(500, {
                    "ok": False,
                    "error": "Voice file was not created"
                })
                return

            self.send_json(200, {
                "ok": True,
                "message": "Arabic dialogue voice created successfully",
                "script_file": SCRIPT_FILE,
                "voice_output": VOICE_OUTPUT,
                "timing_json": VOICE_TIMING_JSON,
                "duration_seconds": round(total_duration, 2),
                "parts_count": len(timing),
                "bob_voice": BOB_VOICE,
                "nova_voice": NOVA_VOICE,
                "file_size_kb": round(os.path.getsize(VOICE_OUTPUT) / 1024, 2)
            })

        except Exception as e:
            self.send_json(500, {
                "ok": False,
                "error": str(e)
            })


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Voice bridge running on http://127.0.0.1:{PORT}")
    print("Endpoint: /generate-voice")
    print(f"Input:  {SCRIPT_FILE}")
    print(f"Output: {VOICE_OUTPUT}")
    print("Mode: Arabic dialogue - Bob male voice + Nova female voice")
    server.serve_forever()