"""Rotina manual: testa download_last_document contra o WeChat real.

Uso:
    python download_last_file.py "<nome>"

Nome com espaço precisa de aspas. Pasta de storage vem do
WECHAT_STORAGE_ROOT no .env, não é mais passada por aqui.
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

    window, config = connect()

    log.info("Localizando arquivo mais recente de %r...", args.nome)
    save_path = wechat.download_last_document(window, args.nome, config.wechat_storage_root)
    log.info("Encontrado em: %s", save_path)


if __name__ == "__main__":
    main()
