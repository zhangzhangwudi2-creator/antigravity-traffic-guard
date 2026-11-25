#!/usr/bin/env python3
"""media_guard.py - PreToolUse/PreInvocation traffic guard for Antigravity."""
import hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv"}
AUDIO_EXT = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
PATH_KEYS = ("Path", "path", "AbsolutePath", "absolutePath", "TargetFile", "targetFile")


def env_int(name, default):
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.flush()


def find_bin(name):
    cand = os.environ.get("FFMPEG_PATH" if name == "ffmpeg" else "FFPROBE_PATH")
    return cand if (cand and os.path.exists(cand)) else shutil.which(name)


def resolve_src(raw_path, data):
    src = Path(os.path.expanduser(str(raw_path)))
    if src.is_absolute():
        return src
    base = data.get("cwd") or (data.get("workspacePaths") or [None])[0]
    return (Path(os.path.expanduser(str(base))) / src) if base else src


def preview_dir(data):
    ad = data.get("artifactDirectoryPath")
    d = (Path(os.path.expanduser(ad)) / "scratch") if ad else (Path(tempfile.gettempdir()) / "media_traffic_guard")
    d.mkdir(parents=True, exist_ok=True)
    return d


def video_duration(src):
    ffprobe = find_bin("ffprobe")
    if not ffprobe:
        return 0.0
    try:
        r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
        return float(r.stdout.strip() or 0.0)
    except Exception:
        return 0.0


def run_ffmpeg(cmd, out_jpg, max_bytes):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=12)
    if r.returncode != 0 or not out_jpg.exists():
        return False, (r.stderr or "ffmpeg failed")[:160]
    sz = out_jpg.stat().st_size
    return (True, "") if (0 < sz < max_bytes) else (False, f"output {sz // 1024} KB exceeds {max_bytes // 1024} KB limit")


def handle_pretool(data):
    call = data.get("toolCall") or {}
    if call.get("name") != "read_file":
        return  # neutral: empty stdout allows execution
    args = call.get("args") or {}
    path_key, raw_path = next(((k, args[k]) for k in PATH_KEYS if args.get(k)), ("Path", ""))
    if not raw_path:
        return
    src = resolve_src(raw_path, data)
    ext = src.suffix.lower()
    if (ext not in VIDEO_EXT and ext not in AUDIO_EXT and ext not in IMAGE_EXT) or not src.is_file():
        return
    sz = src.stat().st_size
    tag = hashlib.sha1(f"{src}|{sz}|{src.stat().st_mtime_ns}".encode("utf-8", errors="replace")).hexdigest()[:10]

    if ext in AUDIO_EXT and sz > env_int("MTG_AUDIO_KB", 300) * 1024:
        return emit({"decision": "deny", "reason": (
            f"[media-traffic-guard] Blocked large audio ({sz / 1048576:.2f} MB) from entering main context. "
            "Use local scripts (ffprobe/transcription) to inspect text output, or temporarily toggle off media-traffic-guard in Customizations if raw audio is truly required."
        )})
    if ext in VIDEO_EXT and sz > env_int("MTG_VIDEO_KB", 512) * 1024:
        ffmpeg = find_bin("ffmpeg")
        if not ffmpeg:
            return emit({"decision": "deny", "reason": f"[media-traffic-guard] Blocked raw video ({sz / 1048576:.2f} MB): ffmpeg not found in PATH."})
        out_jpg = preview_dir(data) / f"media_guard_vid_{tag}.jpg"
        fps_expr = f"fps={6.0 / max(video_duration(src), 1.0):.4f}" if video_duration(src) > 1.2 else "fps=2"
        ok, err = run_ffmpeg([ffmpeg, "-y", "-v", "error", "-i", str(src), "-vf", f"{fps_expr},scale=360:-2,tile=3x2",
                              "-frames:v", "1", "-update", "1", "-q:v", "6", str(out_jpg)], out_jpg, 450 * 1024)
        return emit({"decision": "allow", "overwrite": {path_key: str(out_jpg)}} if ok else
                    {"decision": "deny", "reason": f"[media-traffic-guard] Blocked raw video ({sz / 1048576:.2f} MB); contact-sheet extraction failed ({err})."})
    if ext in IMAGE_EXT and sz > env_int("MTG_IMAGE_KB", 1536) * 1024:
        ffmpeg = find_bin("ffmpeg")
        if not ffmpeg:
            return emit({"decision": "deny", "reason": f"[media-traffic-guard] Blocked large image ({sz / 1048576:.2f} MB): ffmpeg not found in PATH."})
        out_jpg = preview_dir(data) / f"media_guard_img_{tag}.jpg"
        ok, err = run_ffmpeg([ffmpeg, "-y", "-v", "error", "-i", str(src), "-vf", "scale='min(1280,iw)':-2",
                              "-frames:v", "1", "-update", "1", "-q:v", "6", str(out_jpg)], out_jpg, 600 * 1024)
        return emit({"decision": "allow", "overwrite": {path_key: str(out_jpg)}} if ok else
                    {"decision": "deny", "reason": f"[media-traffic-guard] Blocked large image ({sz / 1048576:.2f} MB); resize failed ({err})."})


def handle_preinvoke(data):
    ad, conv_id = data.get("artifactDirectoryPath"), str(data.get("conversationId") or "default")
    media_dir = (Path(os.path.expanduser(ad)) / ".system_generated" / "logs" / "media") if ad else None
    if not media_dir or not media_dir.is_dir():
        return emit({"injectSteps": [], "terminationBehavior": ""})
    mb = sum(e.stat().st_size for e in os.scandir(media_dir) if e.is_file()) / 1048576.0
    bucket = int(mb // env_int("MTG_WARN_MB", 15))
    state_dir = Path(tempfile.gettempdir()) / "media_traffic_guard"
    state_dir.mkdir(parents=True, exist_ok=True)
    flag = state_dir / f"warned_{conv_id}.txt"
    prev = int(flag.read_text().strip()) if flag.exists() and flag.read_text().strip().isdigit() else 0
    if bucket < 1 or bucket <= prev:
        return emit({"injectSteps": [], "terminationBehavior": ""})
    flag.write_text(str(bucket), encoding="utf-8")
    return emit({"injectSteps": [{"systemMessage": {
        "systemMessage": f"Media cache in this conversation has reached {mb:.1f} MB. Remind the user to run /compact or start a new conversation after this step.",
        "metadata": {"user_markdown": f"> ⚠️ **Media Traffic Alert**: This conversation has accumulated **{mb:.1f} MB** of media context. Run `/compact` or open a new chat after this turn to save proxy bandwidth."}
    }}], "terminationBehavior": ""})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}
    if mode == "pretool":
        handle_pretool(data)
    elif mode == "preinvoke":
        handle_preinvoke(data)


if __name__ == "__main__":
    main()
