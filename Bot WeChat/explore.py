"""Diagnóstico via pywinauto — sem efeito colateral, não envia nada.
Lista conversas da sidebar e lê histórico da conversa alvo.

Uso:
    python explore.py "<nome>"
"""

from __future__ import annotations

import argparse
import logging

from wechat import wechat
from config import load_config, setup_logging

log = logging.getLogger("explore")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nome")
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.debug)

    log.info("Procurando janela do WeChat...")
    window = wechat.find_wechat_window()
    log.info("Conectado: %r", window.window_text())

    log.info("Listando sessões da sidebar...")
    for name in wechat.list_sessions(window):
        log.info("  - %s", name)

    log.info("Lendo histórico de '%s'...", args.nome)
    messages = wechat.read_messages(window, args.nome)
    log.info("%d mensagens de texto encontradas:", len(messages))
    for text in messages:
        log.info("  %s", text)


if __name__ == "__main__":
    main()
