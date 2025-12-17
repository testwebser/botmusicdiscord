#!/bin/bash

# ตำกัดการใช้หน่วยความจำ
ulimit -m 45000  # จำกัด RAM ที่ 45MB
ulimit -v 50000  # จำกัด Virtual Memory ที่ 50MB

# ตำความสะอาดแคชเก่า
rm -rf ~/.cache/pip
rm -rf /tmp/discord-*
rm -rf ./.cache/*

# ติดตั้ง dependencies
pip install --no-cache-dir -r requirements.txt

# เริ่มบอทด้วยการจำกัดหน่วยความจำ
python3 -X low_memory main.py 