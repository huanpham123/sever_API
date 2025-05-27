from flask import Flask, request, send_file, render_template, jsonify
import requests
import logging
from io import BytesIO

app = Flask(__name__)

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# API keys (nên dùng biến môi trường trong production)
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
            logger.error("Không tìm thấy file audio trong request")
            return jsonify({"error": "Thiếu file audio"}), 400
            
        audio_file = request.files['audio']
        if audio_file.filename == '':
            logger.error("File audio trống")
            return jsonify({"error": "File audio trống"}), 400

        # Đọc file audio
        try:
            audio_bytes = audio_file.read()
            if len(audio_bytes) == 0:
                logger.error("File audio rỗng")
                return jsonify({"error": "File audio rỗng"}), 400
        except Exception as e:
            logger.error(f"Lỗi đọc file audio: {str(e)}")
            return jsonify({"error": "Lỗi đọc file audio"}), 400

        # Deepgram API
        try:
            logger.debug("Gửi yêu cầu đến Deepgram...")
            deepgram_resp = requests.post(
                "https://api.deepgram.com/v1/listen",
                headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
                data=audio_bytes,
                timeout=10
            )
            deepgram_resp.raise_for_status()
            transcription = deepgram_resp.json().get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0].get('transcript', '')
            if not transcription:
                logger.error("Deepgram không trả về transcription hợp lệ")
                return jsonify({"error": "Lỗi chuyển đổi giọng nói"}), 500
            logger.info(f"Transcription: {transcription}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi Deepgram API: {str(e)}")
            return jsonify({"error": "Lỗi dịch vụ chuyển đổi giọng nói"}), 500

        # Gemini API
        try:
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{
                    "parts": [{"text": transcription}]
                }]
            }
            logger.debug("Gửi yêu cầu đến Gemini...")
            gemini_resp = requests.post(
                gemini_url,
                json=payload,
                timeout=15
            )
            gemini_resp.raise_for_status()
            response_json = gemini_resp.json()
            
            # Xử lý response an toàn
            if not response_json.get('candidates'):
                logger.error("Gemini không trả về câu trả lời hợp lệ")
                return jsonify({"error": "Lỗi xử lý ngôn ngữ tự nhiên"}), 500
                
            gemini_text = response_json['candidates'][0]['content']['parts'][0].get('text', '')
            if not gemini_text:
                logger.error("Nội dung trả về từ Gemini rỗng")
                return jsonify({"error": "Không có phản hồi từ AI"}), 500
            logger.info(f"Gemini response: {gemini_text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi Gemini API: {str(e)}")
            return jsonify({"error": "Lỗi dịch vụ xử lý ngôn ngữ"}), 500

        # TTS API
        try:
            logger.debug("Gửi yêu cầu TTS...")
            tts_resp = requests.get(
                TTS_API_URL,
                params={"text": gemini_text},
                timeout=10
            )
            tts_resp.raise_for_status()
            
            if not tts_resp.content:
                logger.error("TTS trả về nội dung rỗng")
                return jsonify({"error": "Lỗi tạo giọng nói AI"}), 500
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi TTS API: {str(e)}")
            return jsonify({"error": "Lỗi dịch vụ chuyển văn bản thành giọng nói"}), 500

        # Trả về audio
        return send_file(
            BytesIO(tts_resp.content),
            mimetype="audio/mpeg",
            as_attachment=False
        )

    except Exception as e:
        logger.critical(f"Lỗi tổng thể không xác định: {str(e)}", exc_info=True)
        return jsonify({"error": "Lỗi máy chủ nội bộ"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
