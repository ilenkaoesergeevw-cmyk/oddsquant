import argparse

from localclaw import config
from localclaw.server import serve


def main():
    ap = argparse.ArgumentParser(description="LocalClaw 本地单机智能体")
    ap.add_argument("--port", type=int, default=None, help="本地端口（默认 8765）")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = ap.parse_args()
    cfg = config.load()
    if args.port:
        cfg["port"] = args.port
        config.save(cfg)
    serve(cfg, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
