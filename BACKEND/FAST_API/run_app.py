# Руководство к файлу (FAST_API/run_app.py)
# Назначение:
# - Локальный запуск приложения VKMax FastAPI через uvicorn.
# Использование:
# - python -m VKMax.BACKEND.FAST_API.run_app
# - или: uvicorn VKMax.BACKEND.FAST_API.fast_api:app --reload

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("VKMax.BACKEND.FAST_API.fast_api:app", host="127.0.0.1", port=8010, reload=True, log_level="debug")