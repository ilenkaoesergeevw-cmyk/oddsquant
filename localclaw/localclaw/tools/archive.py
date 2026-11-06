import shutil
import time
from pathlib import Path


def zip_path(src, out_dir):
    s = Path(src).expanduser().resolve()
    if not s.exists():
        raise FileNotFoundError(str(s))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    base = f"{s.name}_{time.strftime('%Y%m%d_%H%M%S')}"
    out = shutil.make_archive(
        str(Path(out_dir) / base), "zip", root_dir=str(s.parent), base_dir=s.name
    )
    return {"zip": out, "size": Path(out).stat().st_size}
