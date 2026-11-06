import base64
import time
from pathlib import Path


def capture(out_dir):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    path = Path(out_dir) / f"shot_{int(time.time() * 1000)}.png"
    try:
        import mss
        import mss.tools

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            mss.tools.to_png(img.rgb, img.size, output=str(path))
    except Exception:
        from PIL import ImageGrab

        ImageGrab.grab().save(str(path))
    data = path.read_bytes()
    return {
        "path": str(path),
        "data_url": "data:image/png;base64," + base64.b64encode(data).decode(),
        "size": len(data),
    }
