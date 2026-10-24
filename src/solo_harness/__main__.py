import uvicorn
from solo_harness.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("solo_harness.main:app", host=settings.app_host, port=settings.app_port)
