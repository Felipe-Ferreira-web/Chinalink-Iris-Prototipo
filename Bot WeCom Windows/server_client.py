"""Cliente HTTP pro server Django do módulo "Busca de Suppliers" — fecha o
loop entre a extração de contato (extensão do navegador) e o contato via
WeChat (este módulo). Porta quase direta de `Bot WeCom/server_client.py`
(versão Linux, abandonada) — o endpoint/campos são os mesmos, confirmados
direto no código do server (`server/sourcing/views.py`/`serializers.py`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


@dataclass
class SupplierParaContatar:
    id: int
    name: str
    contact_phone: str


def buscar_suppliers_aguardando_contato(server_url: str) -> list[SupplierParaContatar]:
    """Fornecedores com status=contato_extraido e telefone já extraído."""
    resp = requests.get(
        f"{server_url}/api/suppliers/",
        params={"status": "contato_extraido"},
        timeout=10,
    )
    resp.raise_for_status()
    dados = resp.json()
    itens = dados["results"] if isinstance(dados, dict) and "results" in dados else dados

    suppliers = []
    for item in itens:
        telefone = item.get("contact_phone")
        if not telefone:
            # Sem telefone extraído (só site) não dá pra buscar no WeChat.
            continue
        suppliers.append(
            SupplierParaContatar(id=item["id"], name=item["name"], contact_phone=telefone)
        )
    return suppliers


def marcar_contato_wechat_enviado(server_url: str, supplier_id: int) -> None:
    resp = requests.patch(
        f"{server_url}/api/suppliers/{supplier_id}/",
        json={"status": "contato_wechat_enviado"},
        timeout=10,
    )
    resp.raise_for_status()
