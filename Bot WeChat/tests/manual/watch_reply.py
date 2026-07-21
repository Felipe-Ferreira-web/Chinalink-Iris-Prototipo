"""Rotina manual: vigia conversas e responde mensagem nova, em loop."""

from __future__ import annotations

import logging
import time

import wechat

WATCH_POLL_INTERVAL_SECONDS = 5

log = logging.getLogger("main")


def run(window, text: str) -> None:
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
