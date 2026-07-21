"""Rotina manual: testa download_last_document contra o WeChat real."""

from __future__ import annotations

import logging

import wechat

log = logging.getLogger("main")


def run(window, chat_name: str, save_dir: str) -> None:
    log.info("Baixando arquivo mais recente de %r pra %r...", chat_name, save_dir)
    save_path = wechat.download_last_document(window, chat_name, save_dir)
    log.info("Salvo em: %s", save_path)
