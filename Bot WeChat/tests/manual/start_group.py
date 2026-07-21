"""Rotina manual: testa start_group_chat contra o WeChat real.

Uso:
    python start_group.py <nome1> <nome2> ...
"""

from __future__ import annotations

import argparse
import logging

from _tests_setup import connect
from wechat import wechat

log = logging.getLogger("main")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nomes", nargs="+", metavar="NOME")
    args = parser.parse_args()

    window, _config = connect()

    log.info("Criando grupo com %r...", args.nomes)
    chat_name = wechat.start_group_chat(window, args.nomes)
    if not chat_name:
        log.warning(
            "Algum nome em %r não foi encontrado nos contatos — diálogo cancelado.",
            args.nomes,
        )
        return
    log.info("Conversa de grupo aberta: %r", chat_name)


if __name__ == "__main__":
    main()
