from pathlib import Path
import sys


APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


from server import AppHandler, configure_runtime_context


configure_runtime_context()


class handler(AppHandler):
    pass
