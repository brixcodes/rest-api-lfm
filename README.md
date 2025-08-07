---
title: "LAFAOM-MAO"
emoji: "📋"
colorFrom: "blue"
colorTo: "indigo"
sdk: "docker"
sdk_version: "0.78.0"
app_file: "src/main.py"
pinned: false
---

# ANGARA-Fast-API  0
uvicorn src.main:app  --reload
alembic revision --autogenerate -m "Nom de la migration"
alembic upgrade head
taskkill /F /IM python.exe