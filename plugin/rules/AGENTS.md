# Media Traffic Guard Rules (大媒体流量防火墙规则)

1. **Never directly `read_file` raw video or audio** (`.mp4/.mov/.mkv/.webm/.avi/.wav/.mp3/.flac/.m4a`) or uncompressed images `> 1.5 MB`; inspect the `< 250 KB` ffmpeg contact sheet or resized thumbnail provided by the hook instead.
2. **For audio or unavoidable raw frame-by-frame inspection**: analyze audio via local CLI scripts (`ffprobe` / local transcription) and read only text output. If raw multimodal video/audio inspection is genuinely unavoidable, ask the user to temporarily disable `media-traffic-guard` on the Customizations page and run `/compact` or open a new conversation immediately afterward.
3. **When the media-cache warning triggers**: finish the current step and remind the user to run `/compact` or start a fresh conversation to prevent stateless Base64 re-uploads from burning proxy quota.
