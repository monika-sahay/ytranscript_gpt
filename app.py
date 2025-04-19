from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
import datetime
from urllib.parse import urlparse, parse_qs
import yt_dlp
import re
import os
import logging

# Initialize Flask app and logger
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_video_id(url):
    parsed_url = urlparse(url)
    logger.info(f"Parsing URL: {url}")
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        return parse_qs(parsed_url.query).get('v', [None])[0]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    return None

def format_timestamp(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))

def get_transcript_with_fallback(video_id, lang='en'):
    try:
        logger.info(f"Trying YouTubeTranscriptApi for video_id={video_id}")
        return YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
    except Exception as e:
        logger.warning(f"Primary transcript fetch failed: {e}")
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            for transcript in transcript_list:
                if transcript.language_code == lang:
                    logger.info(f"Using manual transcript in language: {lang}")
                    return transcript.fetch()
                elif transcript.is_generated and transcript.is_translatable:
                    logger.info(f"Using auto-generated transcript and translating to: {lang}")
                    return transcript.translate(lang).fetch()
            raise RuntimeError("No suitable transcript found.")
        except Exception as inner_e:
            logger.error(f"Transcript fallback also failed: {inner_e}")
            raise inner_e

def download_subtitles_with_yt_dlp(video_url, output_file_base="fallback_transcript"):
    try:
        logger.info("Attempting to use yt-dlp for subtitle download...")
        ydl_opts = {
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
        logger.info("yt-dlp subtitle downloaded successfully.")
        return f"{output_file_base}.en.vtt"
    except Exception as e:
        logger.error(f"yt-dlp subtitle download failed: {e}")
        return None

def get_youtube_transcript(video_url):
    logger.info(f"Processing video: {video_url}")
    video_id = extract_video_id(video_url)
    if not video_id:
        logger.error("Failed to extract video ID.")
        raise ValueError("Could not extract video ID from URL.")

    try:
        transcript = get_transcript_with_fallback(video_id, lang='en')
        logger.info("Transcript fetched using YouTubeTranscriptApi")
        return "\n".join([
            f"[{format_timestamp(entry['start'])}] {entry['text']}"
            for entry in transcript
        ])
    except Exception:
        logger.warning("Falling back to yt-dlp for subtitle retrieval...")
        vtt_file = download_subtitles_with_yt_dlp(video_url)
        if vtt_file and os.path.exists(vtt_file):
            with open(vtt_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            text_lines = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith(("WEBVTT", "Kind:", "Language:", "[Music]")) or '-->' in line or 'align:' in line:
                    continue
                cleaned = re.sub(r"<.*?>", "", line)
                text_lines.append(cleaned)

            final_lines = []
            prev_line = ""
            for line in text_lines:
                if line != prev_line:
                    final_lines.append(line)
                    prev_line = line

            logger.info("Transcript retrieved and cleaned from yt-dlp VTT file.")
            return ' '.join(final_lines)
        else:
            logger.error("Transcript could not be retrieved using either method.")
            raise RuntimeError("Transcript could not be retrieved.")

@app.route('/transcript', methods=['POST'])
def get_transcript():
    data = request.json
    url = data.get("url")
    logger.info(f"Received /transcript request with URL: {url}")

    if not url:
        logger.warning("No URL provided.")
        return jsonify({"error": "Missing URL"}), 400

    try:
        transcript = get_youtube_transcript(url)
        logger.info("Transcript successfully returned.")
        return jsonify({"transcript": transcript})
    except Exception as e:
        logger.exception("Failed to return transcript")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
