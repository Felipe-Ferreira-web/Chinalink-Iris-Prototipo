"""Rotina manual: testa set_contact_remark contra o WeChat real.

Uso:
    python set_remark.py <nome> <apelido>
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
    parser.add_argument("apelido")
    args = parser.parse_args()

    window, _config = connect()

    log.info("Definindo remark %r pra %r...", args.apelido, args.nome)
    wechat.set_contact_remark(window, args.nome, args.apelido)
    log.info("Remark definido.")


if __name__ == "__main__":
    main()
