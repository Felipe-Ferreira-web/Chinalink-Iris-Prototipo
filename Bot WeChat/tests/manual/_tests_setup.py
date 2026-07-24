"""Setup comum das rotinas manuais: acha a janela do WeChat, configura log."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from wechat import wechat
from config import load_config, setup_logging

log = logging.getLogger("main")


def connect():
    config = load_config()
    setup_logging(config.debug)
    log.info("Procurando janela do WeChat...")
    window = wechat.find_wechat_window()
    log.info("Conectado: %r", window.window_text())
    return window, config
