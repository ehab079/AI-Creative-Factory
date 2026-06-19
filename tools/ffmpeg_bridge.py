from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
import json
import os
import re
import textwrap
import shutil
import glob

HOST = "0.0.0.0"
PORT = 8099

BASE_DIR = r"D:\AI_Creative_Factory"
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
FINAL_DIR = os.path.join(BASE_DIR, "final")

TALKING_PARTS_DIR = os.path.join(FINAL_DIR, "talking_parts")
TIMING_JSON = os.path.join(FINAL_DIR, "episode_voice_timing.json")

OUTPUT_VIDEO = os.path.join(FINAL_DIR, "episode_final_talking_avatars.mp4")
TEMP_DIR = os.path.join(FINAL_DIR, "talking_video_parts")
CONCAT_LIST = os.path.join(TEMP_DIR, "concat_list.txt")

FONT_FILE = "tahoma.ttf" if os.path.exists(os.path.join(TOOLS_DIR, "tahoma.ttf")) else "arial.ttf"

WIDTH = 1080
HEIGHT = 1920
FPS = 30
TITLE_DURATION = 4.0


def run_cmd(cmd, cwd=None):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr[-8000:])

    return result


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
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def wrap_arabic_lines(text, width=24, max_lines=2):
    text = clean_text(text)
    lines = textwrap.wrap(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False
    )
    return lines[:max_lines]


def write_text_file(filename, text):
    path = os.path.join(TOOLS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return filename


def prepare_title_files():
    title_ar = read_text_file(
        os.path.join(OUTPUT_DIR, "episode_title.txt"),
        "حلقة تعليمية قصيرة"
    )

    title_lines = wrap_arabic_lines(title_ar, width=24, max_lines=2)

    files = []
    for i, line in enumerate(title_lines, start=1):
        filename = f"talking_video_title_ar_{i}.txt"
        write_text_file(filename, line)
        files.append(filename)

    return files


def build_title_filter(title_files):
    filters = ""
    y_start = 750
    line_gap = 95

    for i, filename in enumerate(title_files):
        y = y_start + (i * line_gap)

        filters += (
            f"drawtext=fontfile={FONT_FILE}:textfile={filename}:"
            f"text_shaping=1:"
            f"fontcolor=white:"
            f"fontsize=74:"
            f"borderw=2:"
            f"bordercolor=black@0.50:"
            f"shadowcolor=black@0.85:"
            f"shadowx=0:"
            f"shadowy=4:"
            f"x=(w-text_w)/2:"
            f"y={y},"
        )

    return filters


def create_title_segment(output_path):
    title_files = prepare_title_files()
    title_filter = build_title_filter(title_files)

    filter_complex = (
        f"[0:v]"
        f"{title_filter}"
        f"format=yuv420p,"
        f"setpts=PTS-STARTPTS[v]"
    )

    cmd = [
        "ffmpeg",
        "-y",

        "-f", "lavfi",
        "-t", str(TITLE_DURATION),
        "-i", f"color=c=0x101820:s={WIDTH}x{HEIGHT}:r={FPS}",

        "-f", "lavfi",
        "-t", str(TITLE_DURATION),
        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",

        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "1:a",

        "-r", str(FPS),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-shortest",
        output_path
    ]

    run_cmd(cmd, cwd=TOOLS_DIR)


def load_timing_parts():
    if not os.path.exists(TIMING_JSON):
        raise FileNotFoundError(f"Timing JSON not found:\n{TIMING_JSON}")

    with open(TIMING_JSON, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    parts = data.get("parts", [])

    if not parts:
        raise RuntimeError("No parts found inside episode_voice_timing.json")

    ordered_parts = []

    for item in parts:
        index = int(item.get("index"))
        speaker = item.get("speaker", "").lower().strip()

        if speaker not in ["bob", "nova"]:
            continue

        ordered_parts.append({
            "index": index,
            "speaker": speaker
        })

    ordered_parts.sort(key=lambda x: x["index"])

    if not ordered_parts:
        raise RuntimeError("No valid bob/nova parts found in timing JSON")

    return ordered_parts


def find_talking_video(index, speaker):
    exact_name = f"{index:03d}_{speaker}_talking.mp4"
    exact_path = os.path.join(TALKING_PARTS_DIR, exact_name)

    if os.path.exists(exact_path):
        return exact_path

    pattern = os.path.join(TALKING_PARTS_DIR, f"{index:03d}_{speaker}*.mp4")
    matches = glob.glob(pattern)

    if matches:
        return matches[0]

    raise FileNotFoundError(
        f"Talking video not found for part {index:03d}_{speaker}\n"
        f"Expected something like:\n{exact_path}"
    )


def normalize_talking_segment(input_video, output_path):
    filter_complex = (
        f"[0:v]fps={FPS},split=2[bg_src][fg_src];"

        f"[bg_src]"
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        f"boxblur=30:2,"
        f"eq=contrast=1.04:saturation=1.06[bg];"

        f"[fg_src]"
        f"scale=980:1600:force_original_aspect_ratio=decrease,"
        f"unsharp=5:5:0.6:3:3:0.25[fg];"

        f"[bg][fg]"
        f"overlay=(W-w)/2:170,"
        f"format=yuv420p,"
        f"setpts=PTS-STARTPTS[v]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_video,

        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",

        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-movflags", "+faststart",
        output_path
    ]

    run_cmd(cmd, cwd=TOOLS_DIR)


def safe_concat_path(path):
    return path.replace("\\", "/")


def concat_segments(segment_files, output_path):
    with open(CONCAT_LIST, "w", encoding="utf-8") as f:
        for segment in segment_files:
            f.write(f"file '{safe_concat_path(segment)}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", CONCAT_LIST,
        "-c", "copy",
        "-movflags", "+faststart",
        output_path
    ]

    run_cmd(cmd, cwd=TOOLS_DIR)


def build_final_talking_video():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR, ignore_errors=True)

    os.makedirs(TEMP_DIR, exist_ok=True)

    ordered_parts = load_timing_parts()

    segment_files = []

    title_segment = os.path.join(TEMP_DIR, "000_title.mp4")
    create_title_segment(title_segment)
    segment_files.append(title_segment)

    for item in ordered_parts:
        index = item["index"]
        speaker = item["speaker"]

        talking_video = find_talking_video(index, speaker)
        normalized_segment = os.path.join(
            TEMP_DIR,
            f"{index:03d}_{speaker}_normalized.mp4"
        )

        normalize_talking_segment(talking_video, normalized_segment)
        segment_files.append(normalized_segment)

    concat_segments(segment_files, OUTPUT_VIDEO)

    return {
        "output": OUTPUT_VIDEO,
        "segments_count": len(segment_files),
        "talking_parts_count": len(ordered_parts),
        "mode": "talking_avatars"
    }


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/create-video":
            self.send_json(404, {
                "ok": False,
                "error": "Use /create-video"
            })
            return

        required = [
            TALKING_PARTS_DIR,
            TIMING_JSON,
            os.path.join(TOOLS_DIR, FONT_FILE)
        ]

        missing = [p for p in required if not os.path.exists(p)]

        if missing:
            self.send_json(400, {
                "ok": False,
                "error": "Required files or folders are missing",
                "missing": missing
            })
            return

        try:
            result = build_final_talking_video()

            self.send_json(200, {
                "ok": True,
                "message": "Final talking avatars video created successfully",
                "output": OUTPUT_VIDEO,
                "details": result
            })

        except Exception as e:
            self.send_json(500, {
                "ok": False,
                "error": str(e)
            })


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    print(f"FFmpeg bridge running on http://127.0.0.1:{PORT}")
    print("Endpoint: /create-video")
    print("Mode: final video from talking avatars")
    print(f"Output: {OUTPUT_VIDEO}")
    server.serve_forever()