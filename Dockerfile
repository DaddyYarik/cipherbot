FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY toolkit.py bot.py ./

# Token is provided at runtime (env_file / -e), never baked into the image.
CMD ["python", "bot.py"]
