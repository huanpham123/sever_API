from flask import Flask, request, send_file, render_template
import requests

from io import BytesIO

app = Flask(__name__)

# Load API keys from environment for security
DEEPGRAM_API_KEY = "3cea4c58-d210-4024-b46c-013e605d7caa"
GEMINI_API_KEY = "AIzaSyAb3w5X9Ma0sK5fLbsEoY0wjLfTnydpAv0"
TTS_API_URL = "https://tts-api-tnhy.vercel.app/api/tts"

@app.route('/')
def index():
    # Render the template from templates/index.html
    return render_template('API.html')

@app.route('/process', methods=['POST'])
def process_audio():
    # Lấy file âm thanh từ client
    audio_file = request.files['audio']
    audio_bytes = audio_file.read()

    # Gửi đến Deepgram để chuyển thành văn bản
    deepgram_response = requests.post(
        "https://api.deepgram.com/v1/listen",
        headers={
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "audio/wav"
        },
        data=audio_bytes
    )
    deepgram_response.raise_for_status()
    transcription = deepgram_response.json()['results']['channels'][0]['alternatives'][0]['transcript']
    print(f"Người dùng hỏi: {transcription}")

    # Gửi văn bản đến Gemini
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    gemini_payload = {
        "contents": [
            {"parts": [{"text": transcription} ]}
        ]
    }
    gemini_res = requests.post(gemini_url, json=gemini_payload)
    gemini_res.raise_for_status()
    gemini_text = gemini_res.json()['candidates'][0]['content']['parts'][0]['text']
    print(f"Phản hồi của Gemini: {gemini_text}")

    # Gửi văn bản đến TTS API
    tts_res = requests.get(TTS_API_URL, params={"text": gemini_text})
    tts_res.raise_for_status()

    # Trả file âm thanh
    return send_file(BytesIO(tts_res.content), mimetype="audio/mpeg")

if __name__ == '__main__':
    app.run(debug=True)