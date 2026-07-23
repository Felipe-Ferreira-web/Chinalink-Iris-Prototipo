"""Rotina manual: vigia conversas e imprime mensagens novas, em loop.

Uso:
    python watch_messages.py
"""

from __future__ import annotations

import logging
import time

from _tests_setup import connect
from wechat import wechat

WATCH_POLL_INTERVAL_SECONDS = 5
WATCH_DURATION_SECONDS = 10

log = logging.getLogger("main")


def main() -> None:
    window, _config = connect()

    log.info(
        "Vigiando todas as conversas por %ds (a cada %ds). Ctrl+C pra sair antes.",
        WATCH_DURATION_SECONDS,
        WATCH_POLL_INTERVAL_SECONDS,
    )
    seen_counts: dict[str, int] = {}
    notification_count = 0
    deadline = time.monotonic() + WATCH_DURATION_SECONDS
    try:
        while time.monotonic() < deadline:
            for chat_name in wechat.list_unread_sessions(window):
                messages = wechat.read_messages(window, chat_name)
                if chat_name not in seen_counts:
                    # 1ª vez vendo essa conversa: só grava a base, não notifica
                    # o histórico inteiro como se fosse tudo mensagem nova.
                    seen_counts[chat_name] = len(messages)
                    continue
                seen = seen_counts[chat_name]
                new_messages = messages[seen:]
                seen_counts[chat_name] = len(messages)
                for text in new_messages:
                    notification_count += 1
                    log.info("[%d] %s: %r", notification_count, chat_name, text)
            time.sleep(WATCH_POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        pass
    log.info("Encerrando. Total de notificações: %d.", notification_count)


if __name__ == "__main__":
    main()
