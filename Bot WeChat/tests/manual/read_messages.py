"""Rotina manual: lê e imprime as mensagens de uma conversa."""

from __future__ import annotations

import logging

import wechat

log = logging.getLogger("main")


def run(window, chat_name: str) -> list[str]:
    log.info("Lendo mensagens de '%s'...", chat_name)
    messages = wechat.read_messages(window, chat_name)
    log.info("%d mensagens de texto encontradas:", len(messages))
    for text in messages:
        log.info("  %s", text)
    return messages
