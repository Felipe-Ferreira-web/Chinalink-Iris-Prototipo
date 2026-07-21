"""Rotina manual: vigia conversas e responde mensagem nova, em loop.

Uso:
    python watch_reply.py
    python watch_reply.py "texto"
"""

from __future__ import annotations

import argparse
import logging
import time

from _tests_setup import connect
from wechat import wechat

WATCH_POLL_INTERVAL_SECONDS = 5

log = logging.getLogger("main")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("texto", nargs="?", default=None)
    args = parser.parse_args()

    window, config = connect()
    text = args.texto if args.texto is not None else config.test_message

    log.info(
        "Vigiando todas as conversas (a cada %ds). Ctrl+C pra sair.",
        WATCH_POLL_INTERVAL_SECONDS,
    )
    seen_counts: dict[str, int] = {}
    try:
        while True:
            for chat_name in wechat.list_unread_sessions(window):
                messages = wechat.read_messages(window, chat_name)
                seen = seen_counts.get(chat_name, 0)
                new_messages = messages[seen:]
                seen_counts[chat_name] = len(messages)
                if new_messages:
                    log.info("Mensagem(ns) nova(s) em %r: %r", chat_name, new_messages)
                    wechat.send_message(window, chat_name, text)
                    log.info("Respondido em %r.", chat_name)
            time.sleep(WATCH_POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        log.info("Encerrando.")


if __name__ == "__main__":
    main()
