"""Rotina manual: testa download_last_document contra o WeChat real.

Uso:
    python download_last_file.py "<nome>" "<pasta>"

Nome ou pasta com espaço precisa de aspas.
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
    parser.add_argument("pasta")
    args = parser.parse_args()

    window, _config = connect()

    log.info("Baixando arquivo mais recente de %r pra %r...", args.nome, args.pasta)
    save_path = wechat.download_last_document(window, args.nome, args.pasta)
    log.info("Salvo em: %s", save_path)


if __name__ == "__main__":
    main()
