"""Lê e imprime as mensagens de uma conversa.

Uso:
    python main.py "<nome>"
"""

from __future__ import annotations

import argparse
import logging

from wechat import wechat
from config import load_config, setup_logging

log = logging.getLogger("main")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nome")
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.debug)

    log.info("Procurando janela do WeChat...")
    window = wechat.find_wechat_window()
    log.info("Conectado: %r", window.window_text())

    log.info("Lendo mensagens de '%s'...", args.nome)
    messages = wechat.read_messages(window, args.nome)
    log.info("%d mensagens de texto encontradas:", len(messages))
    for text in messages:
        log.info("  %s", text)


if __name__ == "__main__":
    main()
