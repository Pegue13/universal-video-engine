FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=10000
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py engine.py selftest.py ./
RUN python -m compileall -q /app && python selftest.py
RUN useradd --create-home --uid 10001 engine
USER engine
EXPOSE 10000
CMD ["sh","-c","exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
