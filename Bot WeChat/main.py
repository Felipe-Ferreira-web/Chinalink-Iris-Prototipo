"""Lê e imprime as mensagens de TARGET_CHAT_NAME (do .env).

Testes contra o WeChat real viraram scripts standalone em tests/manual/
(ex.: python tests/manual/add_contact.py <telefone>) — não passam mais
por aqui. Testes de regressão (pywinauto mockado) ficam em tests/pytests/.

Uso:
    python main.py
"""

from __future__ import annotations

import logging

from wechat import wechat
from config import load_config, setup_logging

log = logging.getLogger("main")


def main() -> None:
    config = load_config()
    setup_logging(config.log_level)

    log.info("Procurando janela do WeChat...")
    window = wechat.find_wechat_window()
    log.info("Conectado: %r", window.window_text())

    log.info("Lendo mensagens de '%s'...", config.target_chat_name)
    messages = wechat.read_messages(window, config.target_chat_name)
    log.info("%d mensagens de texto encontradas:", len(messages))
    for text in messages:
        log.info("  %s", text)


if __name__ == "__main__":
    main()
