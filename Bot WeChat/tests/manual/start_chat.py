"""Rotina manual: testa find_or_start_chat contra o WeChat real."""

from __future__ import annotations

import logging

import wechat

log = logging.getLogger("main")


def run(window, contact_name: str) -> None:
    log.info("Abrindo conversa com %r...", contact_name)
    chat_name = wechat.find_or_start_chat(window, contact_name)
    if not chat_name:
        log.warning("%r não encontrado nos contatos.", contact_name)
        return
    log.info("Conversa aberta: %r", chat_name)
