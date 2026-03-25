"""Entry point: python -m metaclaw_memory_sidecar"""

from __future__ import annotations

import argparse
import logging
import sys

import uvicorn

from .config import SidecarConfig
from .server import create_app


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="metaclaw-memory-sidecar",
        description="HTTP sidecar for the MetaClaw Memory system",
    )
    parser.add_argument("--port", type=int, default=None, help="Listen port (default: 19823)")
    parser.add_argument("--host", type=str, default=None, help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--memory-dir", type=str, default=None, help="Memory storage directory")
    parser.add_argument("--scope", type=str, default=None, help="Default memory scope")
    parser.add_argument(
        "--retrieval-mode",
        type=str,
        default=None,
        choices=["keyword", "hybrid", "embedding"],
        help="Retrieval mode",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=["debug", "info", "warning", "error"],
        help="Log level",
    )
    args = parser.parse_args()

    # Start from env vars, then override with CLI flags.
    config = SidecarConfig.from_env()
    if args.port is not None:
        config.port = args.port
    if args.host is not None:
        config.host = args.host
    if args.memory_dir is not None:
        config.memory_dir = args.memory_dir
    if args.scope is not None:
        config.memory_scope = args.scope
    if args.retrieval_mode is not None:
        config.retrieval_mode = args.retrieval_mode
    if args.log_level is not None:
        config.log_level = args.log_level

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    app = create_app(config)
    uvicorn.run(app, host=config.host, port=config.port, log_level=config.log_level)


if __name__ == "__main__":
    main()
