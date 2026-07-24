"""Rotina manual: lê e imprime as mensagens de uma conversa.

Uso:
    python read_messages.py <nome>
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
    chat_name = args.nome

    log.info("Lendo mensagens de '%s'...", chat_name)
    messages = wechat.read_messages(window, chat_name)
    log.info("%d mensagens de texto encontradas:", len(messages))
    for text in messages:
        log.info("  %s", text)


if __name__ == "__main__":
    main()
