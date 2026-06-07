FROM python:3.10-slim

# 1. System dependencies install karo (untrunc ke liye g++, make, aur libav zaroori hai)
RUN apt-get update && apt-get install -y \
    git curl ffmpeg python3-pip wget bash unzip make g++ \
    libavformat-dev libavcodec-dev libavutil-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. untrunc ko download karke compile karo, fir system path me daalo
RUN wget https://github.com/anthwlock/untrunc/archive/master.zip \
    && unzip master.zip \
    && cd untrunc-master \
    && make \
    && cp untrunc /usr/local/bin/ \
    && cd .. \
    && rm -rf untrunc-master master.zip

WORKDIR /app
COPY requirements.txt .

RUN pip3 install wheel
RUN pip3 install --no-cache-dir -U -r requirements.txt

COPY . .
EXPOSE 7860

CMD ["python3", "app.py"]