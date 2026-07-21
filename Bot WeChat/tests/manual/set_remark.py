"""Rotina manual: testa set_contact_remark contra o WeChat real."""

from __future__ import annotations

import logging

import wechat

log = logging.getLogger("main")


def run(window, chat_name: str, remark: str) -> None:
    log.info("Definindo remark %r pra %r...", remark, chat_name)
    wechat.set_contact_remark(window, chat_name, remark)
    log.info("Remark definido.")
