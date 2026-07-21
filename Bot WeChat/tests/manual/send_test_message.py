"""Rotina manual: manda uma mensagem de teste pra uma conversa.

Uso:
    python send_test_message.py
    python send_test_message.py <nome> "texto"
"""

from __future__ import annotations

import argparse
import logging

from _tests_setup import connect
from wechat import wechat

log = logging.getLogger("main")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nome", nargs="?", default=None)
    parser.add_argument("texto", nargs="?", default=None)
    args = parser.parse_args()

    window, config = connect()
    chat_name = args.nome if args.nome is not None else config.target_chat_name
    text = args.texto if args.texto is not None else config.test_message

    log.info("Enviando mensagem de teste para %s: %r", chat_name, text)
    wechat.send_message(window, chat_name, text)
    log.info("Enviado.")


if __name__ == "__main__":
    main()
