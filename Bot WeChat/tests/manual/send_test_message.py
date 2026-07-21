"""Rotina manual: manda uma mensagem de teste pra uma conversa."""

from __future__ import annotations

import logging

import wechat

log = logging.getLogger("main")


def run(window, chat_name: str, text: str) -> None:
    log.info("Enviando mensagem de teste para %s: %r", chat_name, text)
    wechat.send_message(window, chat_name, text)
    log.info("Enviado.")
