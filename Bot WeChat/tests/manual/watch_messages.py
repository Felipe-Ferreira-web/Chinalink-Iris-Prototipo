"""Rotina manual: vigia conversas e imprime mensagens novas, em loop.

Uso:
    python watch_messages.py
"""

from __future__ import annotations

import logging
import time

from _tests_setup import connect
from wechat import wechat

WATCH_DURATION_SECONDS = 5
MAX_MESSAGES_PER_RUN = 10

log = logging.getLogger("main")


def main() -> None:
    window, _config = connect()

    log.info(
        "Vigiando todas as conversas por até %ds (máx. %d mensagens), "
        "encerra antes se não houver mais pendente. Ctrl+C pra sair antes.",
        WATCH_DURATION_SECONDS,
        MAX_MESSAGES_PER_RUN,
    )
    notification_count = 0
    deadline = time.monotonic() + WATCH_DURATION_SECONDS
    try:
        while time.monotonic() < deadline and notification_count < MAX_MESSAGES_PER_RUN:
            # Reconsulta a cada passo (nunca guarda a lista toda de uma vez):
            # uma nova notificação pode chegar, ou a mesma conversa pode
            # receber mensagem nova, enquanto processamos a pendente atual.
            pending = wechat.list_unread_sessions(window)
            if not pending:
                break

            chat_name, unread_count = pending[0]
            # [N] da sidebar é a contagem de não lidas do próprio WeChat —
            # fonte de verdade, não depende de estado local em memória.
            messages = wechat.read_messages(window, chat_name)
            new_messages = messages[-unread_count:] if unread_count else []
            for text in new_messages:
                notification_count += 1
                log.info("[%d] %s: %r", notification_count, chat_name, text)
                if notification_count >= MAX_MESSAGES_PER_RUN:
                    break
    except KeyboardInterrupt:
        pass
    if notification_count >= MAX_MESSAGES_PER_RUN:
        log.warning(
            "Limite de %d mensagens atingido, encerrando cedo (pode haver mais pendente).",
            MAX_MESSAGES_PER_RUN,
        )
    log.info("Encerrando. Total de notificações: %d.", notification_count)


if __name__ == "__main__":
    main()
