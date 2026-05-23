from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'prompts.db'}"
APP_TITLE = "ScriptletAI Prompt Generator"
APP_VERSION = "2.0.0"