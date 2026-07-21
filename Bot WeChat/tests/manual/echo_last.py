"""Rotina manual: reenvia a última mensagem lida (teste de leitura+envio)."""

from __future__ import annotations

import logging

import wechat

log = logging.getLogger("main")


def run(window, chat_name: str, messages: list[str]) -> None:
    if not messages:
        raise RuntimeError(f"Nenhuma mensagem encontrada em '{chat_name}' pra ecoar.")
    last_message = messages[-1]
    log.info("Reenviando a última mensagem lida: %r", last_message)
    wechat.send_message(window, chat_name, last_message)
    log.info("Ecoado.")
