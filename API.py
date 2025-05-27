from flask import Flask, request, send_file, render_template, jsonify
import requests
import logging
from io import BytesIO

app = Flask(__name__)

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# API keys (CHỈ DÙNG CHO PHÁT TRIỂN)
DEEPGRAM_API_KEY = "3cea4c58-d210-4024-b46c-013e605d7caa"
GEMINI_API_KEY = "AIzaSyAb3w5X9Ma0sK5fLbsEoY0wjLfTnydpAv0"
TTS_API_URL = "https://tts-api-tnhy.vercel.app/api/tts"

@app.route('/')
def index():
    return render_template('API.html')

@app.route('/process', methods=['POST'])
def process_audio():
    try:
        # Kiểm tra file audio
        if 'audio' not in request.files:
            return jsonify({"error": "Không tìm thấy file audio"}), 400
            
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "File audio trống"}), 400

        # Đọc file audio
        audio_bytes = audio_file.read()
        if len(audio_bytes) == 0:
            return jsonify({"error": "Dữ liệu audio rỗng"}), 400

        # Deepgram API
        deepgram_resp = requests.post(
            "https://api.deepgram.com/v1/listen",
            headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
            data=audio_bytes,
            timeout=10
        )
        deepgram_resp.raise_for_status()
        transcription = deepgram_resp.json()['results']['channels'][0]['alternatives'][0]['transcript']
        logger.debug(f"Transcription: {transcription}")

        # Gemini API
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{"text": transcription}]
            }]
        }
        gemini_resp = requests.post(gemini_url, json=payload, timeout=15)
        gemini_resp.raise_for_status()
        gemini_text = gemini_resp.json()['candidates'][0]['content']['parts'][0]['text']
        logger.debug(f"Gemini response: {gemini_text}")

        # TTS API
        tts_resp = requests.get(
            TTS_API_URL,
            params={"text": gemini_text},
            timeout=10
        )
        tts_resp.raise_for_status()

        # Trả về audio
        return send_file(
            BytesIO(tts_resp.content),
            mimetype="audio/mpeg"
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Lỗi API: {str(e)}")
        return jsonify({"error": "Lỗi kết nối dịch vụ"}), 500
    except Exception as e:
        logger.error(f"Lỗi không xác định: {str(e)}")
        return jsonify({"error": "Lỗi server nội bộ"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
