"""Rotina manual: testa start_group_chat contra o WeChat real."""

from __future__ import annotations

import logging

import wechat

log = logging.getLogger("main")


def run(window, contact_names: list[str]) -> None:
    log.info("Criando grupo com %r...", contact_names)
    chat_name = wechat.start_group_chat(window, contact_names)
    if not chat_name:
        log.warning(
            "Algum nome em %r não foi encontrado nos contatos — diálogo cancelado.",
            contact_names,
        )
        return
    log.info("Conversa de grupo aberta: %r", chat_name)
