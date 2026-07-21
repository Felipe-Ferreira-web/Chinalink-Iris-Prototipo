"""Rotina manual: testa find_or_start_chat contra o WeChat real.

Uso:
    python start_chat.py <nome>
"""

from __future__ import annotations

import argparse
import logging

from _tests_setup import connect
from wechat import wechat

log = logging.getLogger("main")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nome")
    args = parser.parse_args()

    window, _config = connect()

    log.info("Abrindo conversa com %r...", args.nome)
    chat_name = wechat.find_or_start_chat(window, args.nome)
    if not chat_name:
        log.warning("%r não encontrado nos contatos.", args.nome)
        return
    log.info("Conversa aberta: %r", chat_name)


if __name__ == "__main__":
    main()
