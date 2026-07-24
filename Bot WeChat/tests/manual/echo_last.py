"""Rotina manual: lê a última mensagem de uma conversa e reenvia ela mesma.

Uso:
    python echo_last.py <nome>
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

    messages = wechat.read_messages(window, chat_name)
    if not messages:
        raise RuntimeError(f"Nenhuma mensagem encontrada em '{chat_name}' pra ecoar.")
    last_message = messages[-1]
    log.info("Reenviando a última mensagem lida: %r", last_message)
    wechat.send_message(window, chat_name, last_message)
    log.info("Ecoado.")


if __name__ == "__main__":
    main()
