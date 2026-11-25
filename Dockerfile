FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=10000
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py engine.py media_import.py selftest.py reel_smoke_test.py build_dj_sample.py ./
RUN python -m compileall -q /app && python selftest.py
RUN python reel_smoke_test.py
RUN python build_dj_sample.py
COPY build_henners_documentary.py ./
RUN python build_henners_documentary.py
COPY build_mara_documentary.py app_mara.py ./
RUN python build_mara_documentary.py
COPY build_mara_voice.py app_voice.py ./
RUN (pip install --no-cache-dir 'piper-tts>=1.3,<2' && python -m piper.download_voices es_ES-sharvard-medium && python build_mara_voice.py) || echo 'MARA_VOICE_BUILD_FAILED; preserving silent version'
COPY build_mara_dora.py app_dora.py ./
RUN (pip install --no-cache-dir "kokoro-onnx>=0.4.9,<0.7" && python build_mara_dora.py) || echo "MARA_DORA_BUILD_FAILED; preserving previous versions"
RUN rm -f /tmp/kokoro-v1.0.onnx /tmp/voices-v1.0.bin
COPY build_voice_audition.py app_audition.py ./
RUN (pip install --no-cache-dir edge-tts && python build_voice_audition.py) || echo 'VOICE_AUDITION_FAILED'
COPY build_mara_full_speech.py app_full_speech.py ./
RUN python build_mara_full_speech.py || echo 'MARA_FULL_SPEECH_FAILED; preserving previous exports'
RUN useradd --create-home --uid 10001 engine
USER engine
EXPOSE 10000
CMD ["sh","-c","exec uvicorn app_full_speech:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
