FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps: Python, Java (for Audiveris), wget, curl
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3-pip \
        default-jre-headless \
        wget curl ca-certificates \
        libglib2.0-0 libfreetype6 libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# LilyPond 2.24.4 (apt version too old)
RUN wget -q https://lilypond.org/download/binaries/linux-64/lilypond-2.24.4-linux-64.tar.gz \
    && tar -xzf lilypond-2.24.4-linux-64.tar.gz -C /opt \
    && ln -s /opt/lilypond-2.24.4/bin/lilypond /usr/local/bin/lilypond \
    && rm lilypond-2.24.4-linux-64.tar.gz

# Audiveris 5.10.2 (for PDF input via OMR)
RUN wget -q https://github.com/Audiveris/audiveris/releases/download/5.10.2/Audiveris-5.10.2-ubuntu22.04-x86_64.deb \
    && dpkg -i Audiveris-5.10.2-ubuntu22.04-x86_64.deb \
    && apt-get install -f -y \
    && rm Audiveris-5.10.2-ubuntu22.04-x86_64.deb

# MuseScore 3 headless (for .mscz input); MuseScore 4 via Flatpak not available in Docker
RUN apt-get update && apt-get install -y --no-install-recommends musescore3 xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
