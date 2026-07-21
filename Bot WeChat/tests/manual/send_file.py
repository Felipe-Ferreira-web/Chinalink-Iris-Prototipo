"""Rotina manual: testa send_file contra o WeChat real.

Uso:
    python send_file.py <nome> <caminho>
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
    parser.add_argument("caminho")
    args = parser.parse_args()

    window, _config = connect()

    log.info("Mandando %r pra %r...", args.caminho, args.nome)
    wechat.send_file(window, args.nome, args.caminho)
    log.info("Enviado.")


if __name__ == "__main__":
    main()
