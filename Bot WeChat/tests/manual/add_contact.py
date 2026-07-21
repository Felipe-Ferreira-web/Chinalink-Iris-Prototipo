"""Rotina manual: testa add_contact_by_phone contra o WeChat real."""

from __future__ import annotations

import logging

import wechat

log = logging.getLogger("main")


def run(window, phone: str, text: str) -> None:
    log.info("Adicionando %s como contato novo no WeChat...", phone)
    nickname = wechat.add_contact_by_phone(window, phone, message=text)
    if not nickname:
        log.warning("Telefone %s não corresponde a nenhum contato do WeChat.", phone)
        return
    log.info("Pedido de amizade enviado (apelido no WeChat: %r, mensagem: %r).", nickname, text)
