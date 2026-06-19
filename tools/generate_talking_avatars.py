import os
import re
import shutil
import subprocess
from pathlib import Path

BASE_DIR = r"D:\AI_Creative_Factory"

FINAL_DIR = os.path.join(BASE_DIR, "final")
VOICE_PARTS_DIR = os.path.join(FINAL_DIR, "voice_parts")
TALKING_PARTS_DIR = os.path.join(FINAL_DIR, "talking_parts")

LIP_SYNC_DIR = os.path.join(BASE_DIR, "lip_sync")
WAV2LIP_DIR = os.path.join(LIP_SYNC_DIR, "Wav2Lip")
VENV_PYTHON = os.path.join(LIP_SYNC_DIR, "venv310", "Scripts", "python.exe")

CHECKPOINT = os.path.join(WAV2LIP_DIR, "checkpoints", "wav2lip_gan.pth")

BOB_IMAGE = os.path.join(FINAL_DIR, "teacher_bob_lipsync_ready.png")
NOVA_IMAGE = os.path.join(FINAL_DIR, "nova_lipsync_ready.png")

CLEAN_OLD_OUTPUT = True


def print_header():
    print("=" * 60)
    print(" AI Creative Factory - Generate Talking Avatars")
    print("=" * 60)
    print()


def check_file(path, label):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{label} not found:\n{path}")


def check_required_files():
    check_file(VENV_PYTHON, "Python venv")
    check_file(CHECKPOINT, "Wav2Lip checkpoint")
    check_file(BOB_IMAGE, "Bob lip sync image")
    check_file(NOVA_IMAGE, "Nova lip sync image")

    if not os.path.isdir(VOICE_PARTS_DIR):
        raise FileNotFoundError(f"Voice parts folder not found:\n{VOICE_PARTS_DIR}")

    if not os.path.isdir(WAV2LIP_DIR):
        raise FileNotFoundError(f"Wav2Lip folder not found:\n{WAV2LIP_DIR}")


def prepare_output_folder():
    if CLEAN_OLD_OUTPUT and os.path.exists(TALKING_PARTS_DIR):
        shutil.rmtree(TALKING_PARTS_DIR, ignore_errors=True)

    os.makedirs(TALKING_PARTS_DIR, exist_ok=True)


def get_voice_parts():
    pattern = re.compile(r"^(\d+)_(bob|nova)\.mp3$", re.IGNORECASE)
    parts = []

    for file_name in os.listdir(VOICE_PARTS_DIR):
        match = pattern.match(file_name)

        if not match:
            continue

        index = int(match.group(1))
        speaker = match.group(2).lower()

        audio_path = os.path.join(VOICE_PARTS_DIR, file_name)
        image_path = BOB_IMAGE if speaker == "bob" else NOVA_IMAGE
        output_name = f"{index:03d}_{speaker}_talking.mp4"
        output_path = os.path.join(TALKING_PARTS_DIR, output_name)

        parts.append({
            "index": index,
            "speaker": speaker,
            "audio": audio_path,
            "image": image_path,
            "output": output_path
        })

    parts.sort(key=lambda x: x["index"])

    if not parts:
        raise RuntimeError(
            "No voice parts found. Expected files like:\n"
            "001_bob.mp3\n"
            "002_nova.mp3\n"
            f"inside:\n{VOICE_PARTS_DIR}"
        )

    return parts


def run_wav2lip(part):
    speaker = part["speaker"]
    index = part["index"]

    print("-" * 60)
    print(f"Generating talking video: {index:03d}_{speaker}")
    print(f"Audio : {part['audio']}")
    print(f"Image : {part['image']}")
    print(f"Output: {part['output']}")
    print("-" * 60)

    cmd = [
        VENV_PYTHON,
        "inference.py",
        "--checkpoint_path", CHECKPOINT,
        "--face", part["image"],
        "--audio", part["audio"],
        "--outfile", part["output"],
        "--pads", "0", "20", "0", "0",
        "--resize_factor", "1"
    ]

    result = subprocess.run(
        cmd,
        cwd=WAV2LIP_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        print(result.stdout[-3000:])
        print(result.stderr[-6000:])
        raise RuntimeError(f"Wav2Lip failed on part {index:03d}_{speaker}")

    if not os.path.exists(part["output"]):
        raise RuntimeError(f"Output video was not created:\n{part['output']}")

    print(f"OK: Created {os.path.basename(part['output'])}")
    print()


def main():
    print_header()

    print("Checking required files...")
    check_required_files()
    print("OK: Required files found.")
    print()

    print("Preparing output folder...")
    prepare_output_folder()
    print(f"Output folder: {TALKING_PARTS_DIR}")
    print()

    parts = get_voice_parts()

    print(f"Voice parts found: {len(parts)}")
    for part in parts:
        print(f" - {part['index']:03d}_{part['speaker']}")
    print()

    for part in parts:
        run_wav2lip(part)

    print("=" * 60)
    print("All talking avatars generated successfully.")
    print()
    print("Output folder:")
    print(TALKING_PARTS_DIR)
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)
        print(str(e))
        print("=" * 60)
        raise