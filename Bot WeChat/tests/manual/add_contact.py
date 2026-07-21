"""Rotina manual: testa add_contact_by_phone contra o WeChat real.

Uso:
    python add_contact.py <telefone>
    python add_contact.py <telefone> "mensagem"
"""

from __future__ import annotations

import argparse
import logging

from _tests_setup import connect
from wechat import wechat

log = logging.getLogger("main")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("telefone")
    parser.add_argument("mensagem", nargs="?", default=None)
    args = parser.parse_args()

    window, config = connect()
    text = args.mensagem if args.mensagem is not None else config.test_message

    log.info("Adicionando %s como contato novo no WeChat...", args.telefone)
    nickname = wechat.add_contact_by_phone(window, args.telefone, message=text)
    if not nickname:
        log.warning("Telefone %s não corresponde a nenhum contato do WeChat.", args.telefone)
        return
    log.info("Pedido de amizade enviado (apelido no WeChat: %r, mensagem: %r).", nickname, text)


if __name__ == "__main__":
    main()
