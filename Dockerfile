FROM python:3.10-slim

# Sirf basic tools aur ffmpeg (thumbnails ke liye) install karenge, baki sab hata diya
RUN apt-get update && apt-get install -y \
    git curl ffmpeg python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

RUN pip3 install wheel
RUN pip3 install --no-cache-dir -U -r requirements.txt

COPY . .
EXPOSE 7860

CMD ["python3", "app.py"]
