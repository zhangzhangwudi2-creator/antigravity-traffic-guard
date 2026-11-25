import json, os, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugin" / "scripts" / "media_guard.py"


def run_guard(mode, payload):
    t0 = time.perf_counter()
    r = subprocess.run(
        [sys.executable, str(SCRIPT), mode],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", timeout=25
    )
    ms = (time.perf_counter() - t0) * 1000.0
    if r.returncode != 0:
        raise AssertionError(f"media_guard exited {r.returncode}: {r.stderr}")
    return json.loads(r.stdout), ms


class TestMediaTrafficGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mtg_ci_"))
        self.art = self.tmp / "artifact"
        self.art.mkdir(parents=True, exist_ok=True)
        self.ffmpeg = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_normal_code_passthrough(self):
        out, ms = run_guard("pretool", {
            "toolCall": {"name": "read_file", "args": {"Path": str(SCRIPT)}},
            "artifactDirectoryPath": str(self.art),
        })
        self.assertEqual(out, {})
        self.assertLess(ms, 1000.0)

    def test_real_video_contact_sheet(self):
        if not self.ffmpeg:
            self.skipTest("ffmpeg not available")
        vid = self.tmp / "sample.mp4"
        subprocess.run([
            self.ffmpeg, "-y", "-v", "error", "-f", "lavfi",
            "-i", "testsrc=size=640x480:rate=20:duration=4",
            "-vf", "noise=alls=80:allf=t",
            "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", str(vid)
        ], check=True, timeout=20)
        self.assertGreater(vid.stat().st_size, 512 * 1024)

        out, _ = run_guard("pretool", {
            "toolCall": {"name": "read_file", "args": {"Path": str(vid)}},
            "artifactDirectoryPath": str(self.art),
        })
        self.assertEqual(out.get("decision"), "allow")
        jpg = Path(out["overwrite"]["Path"])
        self.assertTrue(jpg.exists())
        self.assertEqual(jpg.suffix, ".jpg")
        self.assertLess(jpg.stat().st_size, 300 * 1024)

    def test_corrupt_video_denied(self):
        bad = self.tmp / "corrupt.mp4"
        bad.write_bytes(b"\x00\xFF\x12\x34" * (160 * 1024))
        out, _ = run_guard("pretool", {
            "toolCall": {"name": "read_file", "args": {"Path": str(bad)}},
            "artifactDirectoryPath": str(self.art),
        })
        self.assertEqual(out.get("decision"), "deny")

    def test_large_audio_denied(self):
        wav = self.tmp / "big.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * (400 * 1024))
        out, _ = run_guard("pretool", {
            "toolCall": {"name": "read_file", "args": {"Path": str(wav)}},
            "artifactDirectoryPath": str(self.art),
        })
        self.assertEqual(out.get("decision"), "deny")

    def test_large_image_compressed(self):
        if not self.ffmpeg:
            self.skipTest("ffmpeg not available")
        img = self.tmp / "huge.bmp"
        subprocess.run([
            self.ffmpeg, "-y", "-v", "error", "-f", "lavfi",
            "-i", "testsrc2=size=1600x1200:d=1",
            "-frames:v", "1", "-update", "1", str(img)
        ], check=True, timeout=20)
        self.assertGreater(img.stat().st_size, 1536 * 1024)

        out, _ = run_guard("pretool", {
            "toolCall": {"name": "read_file", "args": {"Path": str(img)}},
            "artifactDirectoryPath": str(self.art),
        })
        self.assertEqual(out.get("decision"), "allow")
        jpg = Path(out["overwrite"]["Path"])
        self.assertTrue(jpg.exists())
        self.assertLess(jpg.stat().st_size, 600 * 1024)

    def test_preinvoke_warning_and_empty(self):
        cid = "ci-preinvoke-test"
        flag = Path(tempfile.gettempdir()) / "media_traffic_guard" / f"warned_{cid}.txt"
        if flag.exists():
            flag.unlink()
        try:
            out_empty, _ = run_guard("preinvoke", {"conversationId": cid, "artifactDirectoryPath": str(self.art)})
            self.assertEqual(out_empty, {})

            media_dir = self.art / ".system_generated" / "logs" / "media"
            media_dir.mkdir(parents=True, exist_ok=True)
            (media_dir / "big.bin").write_bytes(b"\x01" * (16 * 1024 * 1024))
            out_warn, _ = run_guard("preinvoke", {"conversationId": cid, "artifactDirectoryPath": str(self.art)})
            self.assertIn("injectSteps", out_warn)
        finally:
            if flag.exists():
                flag.unlink()


if __name__ == "__main__":
    unittest.main()
