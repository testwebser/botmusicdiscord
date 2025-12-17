#!/bin/bash
# ดาวน์โหลด FFmpeg static binary สำหรับ Linux

echo "📥 Downloading FFmpeg static binary..."

# สร้างโฟลเดอร์
mkdir -p /opt/render/project/src/bin

# ดาวน์โหลด FFmpeg static build
wget -q https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0/ffmpeg-linux-x64 -O /opt/render/project/src/bin/ffmpeg

# ทำให้รันได้
chmod +x /opt/render/project/src/bin/ffmpeg

# เช็คว่าทำงานหรือเปล่า
/opt/render/project/src/bin/ffmpeg -version

echo "✅ FFmpeg installed successfully!"
