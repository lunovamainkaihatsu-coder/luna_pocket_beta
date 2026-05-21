import runpy
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
runpy.run_path(str(BASE_DIR / "settings" / "app.py"), run_name="__main__")
