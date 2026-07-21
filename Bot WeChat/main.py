"""Testa as funções básicas do WeChat mapeadas em wechat.py.

Substitui a versão antiga baseada no wxauto4 (abandonado — ver README).

As rotinas de cada teste vivem em tests/manual/ (uma por arquivo); este
módulo só faz o parsing de argumentos e despacha pra elas.

Uso:
    python main.py                     # só lê e imprime as mensagens de TARGET_CHAT_NAME
    python main.py --test-reply        # além de ler, manda TEST_MESSAGE (do .env) antes
    python main.py --test-reply "oi"   # manda esse texto específico em vez de TEST_MESSAGE
    python main.py --echo-last         # lê a última mensagem de TARGET_CHAT_NAME e reenvia ela mesma
    python main.py --test-add-contact <telefone>          # testa add_contact_by_phone, usa TEST_MESSAGE
    python main.py --test-add-contact <telefone> "texto"  # idem, com mensagem específica
    python main.py --test-start-chat <nome>                # testa find_or_start_chat com um contato já existente
    python main.py --test-start-group <nome1> <nome2> ...  # testa start_group_chat com 2+ contatos já existentes
    python main.py --test-send-file <nome> <caminho>        # testa send_file com um arquivo local
    python main.py --watch-reply                            # vigia todas as conversas, responde mensagem nova com TEST_MESSAGE
    python main.py --watch-reply "texto"                    # idem, com texto específico
    python main.py --test-download-last-file <nome> <pasta>  # testa download_last_document
    python main.py --test-set-remark <nome> <apelido>        # testa set_contact_remark
"""

from __future__ import annotations

import argparse
import logging

import wechat
from config import load_config, setup_logging
from tests.manual import (
    add_contact,
    download_last_file,
    echo_last,
    read_messages,
    send_file,
    send_test_message,
    set_remark,
    start_chat,
    start_group,
    watch_reply,
)

log = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test-reply",
        nargs="?",
        const="__use_config__",
        default=None,
        help="Envia uma mensagem de teste para TARGET_CHAT_NAME antes de ler. "
        "Sem valor, usa TEST_MESSAGE do .env.",
    )
    parser.add_argument(
        "--echo-last",
        action="store_true",
        help="Lê a última mensagem de TARGET_CHAT_NAME e reenvia ela mesma "
        "(teste de leitura, não só de envio).",
    )
    parser.add_argument(
        "--test-add-contact",
        nargs="+",
        metavar=("TELEFONE", "MENSAGEM"),
        help="Testa add_contact_by_phone: adiciona TELEFONE como contato novo "
        "e manda MENSAGEM (ou TEST_MESSAGE do .env, se omitida).",
    )
    parser.add_argument(
        "--test-start-chat",
        metavar="NOME",
        help="Testa find_or_start_chat: abre conversa com um contato já existente "
        "chamado NOME (com ou sem sessão na sidebar ainda).",
    )
    parser.add_argument(
        "--test-start-group",
        nargs="+",
        metavar="NOME",
        help="Testa start_group_chat: cria grupo com os NOME(s) informados "
        "(contatos já existentes; precisa de 2+ pra virar grupo de verdade).",
    )
    parser.add_argument(
        "--test-send-file",
        nargs=2,
        metavar=("NOME", "CAMINHO"),
        help="Testa send_file: manda o arquivo em CAMINHO (local, caminho completo) "
        "pra conversa NOME.",
    )
    parser.add_argument(
        "--watch-reply",
        nargs="?",
        const="__use_config__",
        default=None,
        help="Vigia todas as conversas (list_unread_sessions) e responde mensagem "
        "nova com esse texto (ou TEST_MESSAGE do .env, se omitido). Loop contínuo, "
        "Ctrl+C pra sair.",
    )
    parser.add_argument(
        "--test-download-last-file",
        nargs=2,
        metavar=("NOME", "PASTA"),
        help="Testa download_last_document: baixa o arquivo mais recente de NOME "
        "pra dentro de PASTA.",
    )
    parser.add_argument(
        "--test-set-remark",
        nargs=2,
        metavar=("NOME", "APELIDO"),
        help="Testa set_contact_remark: define APELIDO (remark) pro contato NOME.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    setup_logging(config.log_level)

    log.info("Procurando janela do WeChat...")
    window = wechat.find_wechat_window()
    log.info("Conectado: %r", window.window_text())

    if args.test_add_contact is not None:
        phone = args.test_add_contact[0]
        text = args.test_add_contact[1] if len(args.test_add_contact) > 1 else config.test_message
        add_contact.run(window, phone, text)
        return

    if args.test_start_chat is not None:
        start_chat.run(window, args.test_start_chat)
        return

    if args.test_start_group is not None:
        start_group.run(window, args.test_start_group)
        return

    if args.test_send_file is not None:
        chat_name, filepath = args.test_send_file
        send_file.run(window, chat_name, filepath)
        return

    if args.test_download_last_file is not None:
        chat_name, save_dir = args.test_download_last_file
        download_last_file.run(window, chat_name, save_dir)
        return

    if args.test_set_remark is not None:
        chat_name, remark = args.test_set_remark
        set_remark.run(window, chat_name, remark)
        return

    if args.watch_reply is not None:
        text = config.test_message if args.watch_reply == "__use_config__" else args.watch_reply
        watch_reply.run(window, text)
        return

    if args.test_reply is not None:
        text = config.test_message if args.test_reply == "__use_config__" else args.test_reply
        send_test_message.run(window, config.target_chat_name, text)

    messages = read_messages.run(window, config.target_chat_name)

    if args.echo_last:
        echo_last.run(window, config.target_chat_name, messages)


if __name__ == "__main__":
    main()
