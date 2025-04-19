
from flask import Flask, request, jsonify

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
import datetime
from urllib.parse import urlparse, parse_qs
import yt_dlp
import re
import os
import logging
import time
import traceback

def extract_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        return parse_qs(parsed_url.query).get('v', [None])[0]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    return None

def format_timestamp(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))

def get_transcript_with_fallback(video_id, lang='en'):
    try:
        return YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
    except Exception:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            for transcript in transcript_list:
                if transcript.language_code == lang:
                    return transcript.fetch()
                elif transcript.is_generated and transcript.is_translatable:
                    return transcript.translate(lang).fetch()
            raise RuntimeError("No suitable transcript found.")
        except Exception as inner_e:
            raise inner_e

def download_subtitles_with_yt_dlp(video_url, output_file_base="fallback_transcript"):
    try:
        ydl_opts = {
    'cookiefile': 'cookies.txt',
    'skip_download': True,
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitleslangs': ['en'],
    'subtitlesformat': 'vtt',
    'outtmpl': f"{output_file_base}.%(ext)s",
    'noplaylist': True
}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return f"{output_file_base}.en.vtt"
    except Exception:
        return None

def get_youtube_transcript(video_url):
    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError("Could not extract video ID from URL.")

    try:
        # Try YouTubeTranscriptApi
        transcript = get_transcript_with_fallback(video_id, lang='en')
        return "\n".join([
            f"[{format_timestamp(entry['start'])}] {entry['text']}"
            for entry in transcript
        ])
    except Exception:
        # Fallback to yt-dlp
        vtt_file = download_subtitles_with_yt_dlp(video_url)
        if vtt_file and os.path.exists(vtt_file):
            with open(vtt_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Clean and parse VTT
            text_lines = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith(("WEBVTT", "Kind:", "Language:", "[Music]")) or '-->' in line or 'align:' in line:
                    continue
                cleaned = re.sub(r"<.*?>", "", line)
                text_lines.append(cleaned)

            # Deduplicate lines
            final_lines = []
            prev_line = ""
            for line in text_lines:
                if line != prev_line:
                    final_lines.append(line)
                    prev_line = line

            return ' '.join(final_lines)
        else:
            raise RuntimeError("Transcript could not be retrieved.")






app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/transcript', methods=['POST'])
def get_transcript():
    start_time = time.time()

    data = request.json
    url = data.get("url")
    user_agent = request.headers.get("User-Agent", "Unknown")

    logger.info(f"📩 Received /transcript request")
    logger.info(f"🔗 URL: {url}")
    logger.info(f"🧠 User-Agent: {user_agent}")

    if not url:
        logger.warning("🚫 No URL provided.")
        return jsonify({"error": "Missing URL", "hint": "Make sure you include a 'url' key in your POST JSON."}), 400

    try:
        transcript = get_youtube_transcript(url)  # your existing function
        duration = time.time() - start_time
        logger.info(f"✅ Transcript successfully returned in {duration:.2f}s")
        return jsonify({"transcript": transcript})

    except Exception as e:
        duration = time.time() - start_time
        logger.error("❌ Error occurred while retrieving transcript:")
        traceback.print_exc()
        return jsonify({
            "error": "Transcript could not be retrieved.",
            "details": str(e),
            "hint": "Check if the video has subtitles or if YouTube blocked the request (e.g. CAPTCHA).",
            "duration_seconds": round(duration, 2),
            "user_agent": user_agent
        }), 500

@app.route('/privacy', methods=['GET'])
def privacy_policy():
    return """
    <h1>Privacy Policy</h1>
    <p>This app does not collect or store any personal data.</p>
    <p>Transcripts are generated on-the-fly and are not saved.</p>
    <p>If you have any concerns, contact: your-email@example.com</p>
    """, 200

if __name__ == '__main__':
    app.run()
