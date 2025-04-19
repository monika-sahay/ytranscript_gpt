# YouTube Transcript API 🎬📝

This Flask app extracts and cleans the transcript from a YouTube video using either the `youtube-transcript-api` or `yt-dlp` as a fallback.

---

## 🚀 Features

- Extracts transcript using `youtube-transcript-api`
- Falls back to downloading subtitles using `yt-dlp` if needed
- Cleans timestamps, HTML tags, and duplicate lines
- Returns transcript via a simple REST API

---

## 📦 Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```
