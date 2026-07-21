"""Rotina manual: testa send_file contra o WeChat real."""

from __future__ import annotations

import logging

import wechat

log = logging.getLogger("main")


def run(window, chat_name: str, filepath: str) -> None:
    log.info("Mandando %r pra %r...", filepath, chat_name)
    wechat.send_file(window, chat_name, filepath)
    log.info("Enviado.")
