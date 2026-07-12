# ----- runtime stage -----
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for Qt + matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libxkbcommon0 libdbus-1-3 \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY DATA/ ./DATA/

# ----- build stage: freeze into a folder via PyInstaller -----
FROM runtime AS builder

RUN pip install --no-cache-dir pyinstaller

RUN cd src && pyinstaller \
    --noconfirm \
    --onefile \
    --windowed \
    --name "WeChatAnalyzer" \
    --add-data "../DATA:DATA" \
    --hidden-import pandas \
    --hidden-import xlrd \
    --hidden-import openpyxl \
    --hidden-import matplotlib \
    --hidden-import PySide6 \
    --hidden-import beautifulsoup4 \
    --hidden-import bs4 \
    --hidden-import mplcursors \
    main.py

# ----- final: just the binary -----
FROM python:3.11-slim AS final
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk && rm -rf /var/lib/apt/lists/*
WORKDIR /output
COPY --from=builder /app/src/dist/WeChatAnalyzer .
RUN chmod +x WeChatAnalyzer
