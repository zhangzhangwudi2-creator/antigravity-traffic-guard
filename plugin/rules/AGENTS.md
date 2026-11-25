# Media Traffic Guard Rules (大媒体流量防火墙规则)

1. **Never directly `read_file` raw video or audio** (`.mp4/.mov/.mkv/.webm/.avi/.wav/.mp3/.flac/.m4a`) or uncompressed images `> 1.5 MB` in the main conversation; inspect `< 250 KB` ffmpeg contact sheets or thumbnails instead.
2. **When full frame-by-frame video or raw audio inspection is genuinely required**: delegate to a 1-turn disposable subagent (`invoke_subagent`) in an isolated context and instruct it to return text-only findings without bringing raw media back into the main thread.
3. **When the media-cache warning triggers**: finish the current step and remind the user to run `/compact` or start a fresh conversation to stop stateless Base64 re-uploads from burning proxy quota.
