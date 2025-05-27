from flask import Flask, request, send_file, render_template
import requests
import os
from io import BytesIO

app = Flask(__name__)

# Inline API keys (đảm bảo hoạt động)
DEEPGRAM_API_KEY = "3cea4c58-d210-4024-b46c-013e605d7caa"
GEMINI_API_KEY = "AIzaSyAb3w5X9Ma0sK5fLbsEoY0wjLfTnydpAv0"
TTS_API_URL = "https://tts-api-tnhy.vercel.app/api/tts"

@app.route('/')
def index():
    # Render trang front-end
    return render_template('API.html')

@app.route('/process', methods=['POST'])
def process_audio():
    # Nhận file audio từ client (WebM, WAV...)
    audio_file = request.files.get('audio')
    audio_bytes = audio_file.read()

    # Gửi tới Deepgram (Deepgram tự detect định dạng)
    deepgram_resp = requests.post(
        "https://api.deepgram.com/v1/listen",
        headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
        data=audio_bytes
    )
    deepgram_resp.raise_for_status()
    transcription = deepgram_resp.json()['results']['channels'][0]['alternatives'][0]['transcript']
    print(f"[Deepgram] Transcription: {transcription}")

    # Gửi đến Gemini LLM
    gemini_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
    )
    payload = {"contents":[{"parts":[{"text": transcription}]}]}
    gemini_resp = requests.post(gemini_url, json=payload)
    gemini_resp.raise_for_status()
    gemini_text = gemini_resp.json()['candidates'][0]['content']['parts'][0]['text']
    print(f"[Gemini] Response: {gemini_text}")

    # Gửi đến TTS API
    tts_resp = requests.get(TTS_API_URL, params={"text": gemini_text})
    tts_resp.raise_for_status()

    # Trả lại audio cho client
    return send_file(BytesIO(tts_resp.content), mimetype="audio/mpeg")

if __name__ == '__main__':
    # Chạy local
    app.run(debug=True, host='0.0.0.0', port=5000)
