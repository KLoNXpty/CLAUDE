#!/usr/bin/env python3
"""
INDAGO Forense — Servidor de Captura Automática
Corre en localhost:8765 junto al archivo INDAGO-FORENSE.html
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess, os, json, hashlib, base64, tempfile, shutil, requests, socket
from datetime import datetime, timezone
from pathlib import Path
import urllib.parse

app = Flask(__name__)
CORS(app)  # Allow HTML file (file://) to call the API

STORAGE_DIR = Path(tempfile.gettempdir()) / "indago_evidence"
STORAGE_DIR.mkdir(exist_ok=True)

APP_VERSION = "2.0.0"

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def to_base64(path) -> str:
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def get_mime(path):
    ext = Path(path).suffix.lower()
    return {'jpg':'image/jpeg','jpeg':'image/jpeg','png':'image/png','gif':'image/gif',
            'webp':'image/webp','mp4':'video/mp4','webm':'video/webm','mkv':'video/x-matroska'}.get(ext, 'application/octet-stream')

@app.route('/api/status')
def status():
    ytdlp_ok = shutil.which('yt-dlp') is not None
    playwright_ok = False
    try:
        from playwright.sync_api import sync_playwright
        playwright_ok = True
    except ImportError:
        pass
    return jsonify({
        'status': 'online',
        'version': APP_VERSION,
        'yt_dlp': ytdlp_ok,
        'playwright': playwright_ok,
        'storage_dir': str(STORAGE_DIR)
    })

@app.route('/api/capture-page', methods=['POST'])
def capture_page():
    """Fetch a web page: HTML source, screenshot, server IP, headers"""
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL requerida'}), 400

    result = {
        'url': url,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'title': '',
        'html': '',
        'sha256_html': '',
        'screenshot_b64': '',
        'sha256_screenshot': '',
        'server_ip': '',
        'headers': {},
        'status_code': None,
        'content_type': '',
        'error': None
    }

    # Get server IP
    try:
        hostname = urllib.parse.urlparse(url).hostname
        result['server_ip'] = socket.gethostbyname(hostname)
    except:
        pass

    # Fetch page
    headers_req = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers_req, timeout=30, allow_redirects=True)
        result['status_code'] = resp.status_code
        result['content_type'] = resp.headers.get('content-type', '')
        result['headers'] = dict(resp.headers)
        result['html'] = resp.text
        result['sha256_html'] = sha256_bytes(resp.content)
        # Extract title
        import re
        m = re.search(r'<title[^>]*>(.*?)</title>', resp.text, re.IGNORECASE | re.DOTALL)
        if m:
            result['title'] = m.group(1).strip()[:200]
    except Exception as e:
        result['error'] = str(e)

    # Screenshot with Playwright (optional)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            page.goto(url, timeout=30000, wait_until='networkidle')
            if not result['title']:
                result['title'] = page.title()
            sc_path = STORAGE_DIR / f"screenshot_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
            page.screenshot(path=str(sc_path), full_page=True)
            browser.close()
            result['screenshot_b64'] = 'data:image/png;base64,' + to_base64(sc_path)
            result['sha256_screenshot'] = sha256_file(sc_path)
            sc_path.unlink(missing_ok=True)
    except Exception as e:
        result['screenshot_error'] = str(e)

    return jsonify(result)


@app.route('/api/download-media', methods=['POST'])
def download_media():
    """Download video/audio from any yt-dlp supported platform"""
    data = request.json
    url = data.get('url', '').strip()
    download_video = data.get('download_video', True)
    if not url:
        return jsonify({'error': 'URL requerida'}), 400

    if not shutil.which('yt-dlp'):
        return jsonify({'error': 'yt-dlp no está instalado. Ejecute: pip install yt-dlp'}), 500

    work_dir = STORAGE_DIR / f"media_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    work_dir.mkdir()

    result = {
        'url': url,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'platform': '',
        'title': '',
        'description': '',
        'thumbnail_b64': '',
        'sha256_thumbnail': '',
        'sha256_video': '',
        'video_path': '',
        'video_size_mb': 0,
        'duration': '',
        'resolution': '',
        'view_count': None,
        'like_count': None,
        'comment_count': None,
        'upload_date': '',
        'author': '',
        'author_id': '',
        'post_id': '',
        'comments': [],
        'metadata_json': {},
        'ytdlp_command': '',
        'error': None
    }

    try:
        # Build yt-dlp command
        cmd_parts = [
            'yt-dlp',
            '--write-info-json',
            '--write-thumbnail',
            '--write-description',
            '--write-comments',
            '--no-playlist',
            '-o', str(work_dir / '%(id)s.%(ext)s'),
        ]

        if download_video:
            cmd_parts += ['-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best']
        else:
            cmd_parts += ['--skip-download']

        cmd_parts.append(url)
        result['ytdlp_command'] = ' '.join(cmd_parts)

        proc = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=300, cwd=str(work_dir))

        # Find info.json
        info_files = list(work_dir.glob('*.info.json'))
        if info_files:
            with open(info_files[0]) as f:
                info = json.load(f)
            result['metadata_json'] = info
            result['title'] = info.get('title', '')
            result['description'] = (info.get('description', '') or '')[:2000]
            result['platform'] = info.get('extractor_key', '') or info.get('extractor', '')
            result['view_count'] = info.get('view_count')
            result['like_count'] = info.get('like_count')
            result['comment_count'] = info.get('comment_count')
            result['author'] = info.get('uploader', '') or info.get('channel', '')
            result['author_id'] = info.get('uploader_id', '') or info.get('channel_id', '')
            result['post_id'] = info.get('id', '')
            result['upload_date'] = info.get('upload_date', '')
            if result['upload_date'] and len(result['upload_date']) == 8:
                d = result['upload_date']
                result['upload_date'] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            # Duration
            dur = info.get('duration')
            if dur:
                m, s = divmod(int(dur), 60)
                result['duration'] = f"{m:02d}:{s:02d}"
            # Resolution
            w, h = info.get('width'), info.get('height')
            if w and h:
                result['resolution'] = f"{w}x{h}"
            # Comments (up to 50)
            comments_raw = info.get('comments', []) or []
            result['comments'] = [
                {
                    'id': c.get('id', ''),
                    'autor': c.get('author', ''),
                    'texto': c.get('text', ''),
                    'fecha': c.get('timestamp', ''),
                    'likes': c.get('like_count', 0)
                }
                for c in (comments_raw[:50] if comments_raw else [])
            ]

        # Find thumbnail
        thumb_exts = ['.jpg', '.jpeg', '.png', '.webp']
        for ext in thumb_exts:
            thumb_files = list(work_dir.glob(f'*{ext}'))
            non_info = [f for f in thumb_files if '.info' not in f.name]
            if non_info:
                thumb_path = non_info[0]
                mime = get_mime(str(thumb_path))
                result['thumbnail_b64'] = f'data:{mime};base64,' + to_base64(thumb_path)
                result['sha256_thumbnail'] = sha256_file(thumb_path)
                break

        # Find video file
        if download_video:
            video_exts = ['.mp4', '.mkv', '.webm', '.avi', '.mov']
            for ext in video_exts:
                video_files = [f for f in work_dir.glob(f'*{ext}') if f.stat().st_size > 10000]
                if video_files:
                    vf = video_files[0]
                    result['sha256_video'] = sha256_file(vf)
                    result['video_path'] = str(vf)
                    result['video_size_mb'] = round(vf.stat().st_size / 1048576, 2)
                    break

    except subprocess.TimeoutExpired:
        result['error'] = 'Timeout — el video tardó demasiado en descargarse'
    except Exception as e:
        result['error'] = str(e)

    return jsonify(result)


@app.route('/api/fetch-image', methods=['POST'])
def fetch_image():
    """Download an image from a URL"""
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL requerida'}), 400

    result = {
        'url': url,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'image_b64': '',
        'sha256': '',
        'content_type': '',
        'size_kb': 0,
        'headers': {},
        'server_ip': '',
        'error': None
    }

    try:
        hostname = urllib.parse.urlparse(url).hostname
        result['server_ip'] = socket.gethostbyname(hostname)
    except:
        pass

    try:
        headers_req = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
        resp = requests.get(url, headers=headers_req, timeout=30)
        result['content_type'] = resp.headers.get('content-type', 'image/jpeg')
        result['headers'] = dict(resp.headers)
        result['size_kb'] = round(len(resp.content) / 1024, 1)
        result['sha256'] = sha256_bytes(resp.content)
        mime = result['content_type'].split(';')[0].strip()
        result['image_b64'] = f'data:{mime};base64,' + base64.b64encode(resp.content).decode()
    except Exception as e:
        result['error'] = str(e)

    return jsonify(result)


@app.route('/api/download-video-file', methods=['POST'])
def download_video_file():
    """Return the actual video file for download"""
    data = request.json
    video_path = data.get('video_path', '')
    if not video_path or not Path(video_path).exists():
        return jsonify({'error': 'Archivo no encontrado'}), 404
    return send_file(video_path, as_attachment=True)


if __name__ == '__main__':
    print(f"""
╔══════════════════════════════════════════════════════╗
║  INDAGO Forense v{APP_VERSION} — Servidor de Captura      ║
║  Escuchando en: http://localhost:8765                 ║
║  Abra INDAGO-FORENSE.html en su navegador            ║
╚══════════════════════════════════════════════════════╝
    """)
    app.run(host='127.0.0.1', port=8765, debug=False)
