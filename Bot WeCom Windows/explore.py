"""Diagnóstico do wxauto4 — sem efeito colateral, não envia nada.

Roda isso primeiro. Conecta na instância do WeChat já aberta, imprime o
que a lib consegue enxergar (sessões, histórico da conversa alvo) e para
por aí. Serve pra confirmar que o básico funciona antes de tentar enviar
mensagem de verdade (ver main.py).
"""

from __future__ import annotations

import logging

from config import load_config, setup_logging

log = logging.getLogger("explore")


def main() -> None:
    config = load_config()
    setup_logging(config.log_level)

    log.info("Conectando ao WeChat já aberto...")
    from wxauto4 import WeChat

    wx = WeChat(debug=True)
    log.info("Conectado. nickname=%s", wx.nickname)
    log.info("path=%s", wx.path)
    log.info("dir=%s", wx.dir)

    log.info("Listando sessões da sidebar...")
    sessions = wx.GetSession()
    for session in sessions:
        log.info("  - %s (não lidas: %s)", session.name, session.unread_count)

    log.info("Navegando até a conversa alvo: %s", config.target_chat_name)
    wx.ChatWith(config.target_chat_name)

    log.info("Lendo histórico da conversa aberta...")
    messages = wx.GetAllMessage()
    log.info("%d mensagens encontradas:", len(messages))
    for msg in messages:
        log.info("  [%s] %s: %s", msg.attr, getattr(msg, "sender", "?"), msg.content)


if __name__ == "__main__":
    main()
