"""Diagnóstico via pywinauto — sem efeito colateral, não envia nada.

Roda isso primeiro. Conecta na janela do WeChat já aberta, lista as
conversas da sidebar e lê o histórico da conversa alvo. Substitui a
versão antiga baseada no wxauto4 (abandonado — ver README).
"""

from __future__ import annotations

import logging

import wechat
from config import load_config, setup_logging

log = logging.getLogger("explore")


def main() -> None:
    config = load_config()
    setup_logging(config.log_level)

    log.info("Procurando janela do WeChat...")
    window = wechat.find_wechat_window()
    log.info("Conectado: %r", window.window_text())

    log.info("Listando sessões da sidebar...")
    for name in wechat.list_sessions(window):
        log.info("  - %s", name)

    log.info("Lendo histórico de '%s'...", config.target_chat_name)
    messages = wechat.read_messages(window, config.target_chat_name)
    log.info("%d mensagens de texto encontradas:", len(messages))
    for text in messages:
        log.info("  %s", text)


if __name__ == "__main__":
    main()
