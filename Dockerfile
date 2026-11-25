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
COPY build_mara_full_speech.py build_mara_cpu.py app_full_speech.py ./
ARG MARA_SPEECH_CLIPS
RUN python build_mara_full_speech.py collect || echo 'MARA_COLLECT_FAILED'
RUN (python -m venv /tmp/mara-voice-venv && /tmp/mara-voice-venv/bin/pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.8.0 torchaudio==2.8.0 && /tmp/mara-voice-venv/bin/pip install --no-cache-dir 'numpy==1.26.4' 'librosa==0.10.2.post1' 'resampy==0.4.3' s3tokenizer 'transformers==4.46.3' 'diffusers==0.29.0' 'omegaconf==2.3.0' 'resemble-perth==1.0.1' 'silero-vad==5.1.2' 'conformer==0.3.2' safetensors 'huggingface_hub<1' soundfile && HF_HOME=/tmp/mara-hf-cache timeout 420 /tmp/mara-voice-venv/bin/python build_mara_cpu.py) || echo 'MARA_CPU_FAILED'; rm -rf /tmp/mara-voice-venv /tmp/mara-hf-cache /tmp/mara-chatterbox-model /tmp/mara-chatterbox-reference.wav; python build_mara_full_speech.py || echo 'MARA_ASSEMBLY_FAILED'
RUN useradd --create-home --uid 10001 engine
USER engine
EXPOSE 10000
CMD ["sh","-c","exec uvicorn app_full_speech:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
