"""Calibração interativa do fluxo "buscar contato por telefone + adicionar".

A maioria dos passos tem rótulo de texto visível — pra esses, a automação
(`wechat_client.search_and_add_contact`) NÃO usa coordenada fixa, ela acha o
texto por OCR toda vez que roda. Aqui só capturamos QUAL texto procurar (não
onde ele está), lendo o rótulo perto de onde você posicionar o mouse — então
essa calibração não precisa ser refeita se a janela mudar de tamanho/posição,
só se o texto do botão mudar de verdade (outra versão do WeChat, outro
idioma).

Só `shortcuts_button` é ícone-only (sem texto visível, só legenda ao passar o
mouse) — pra esse guardamos posição + legenda; em runtime, se a posição
salva não bater mais com a legenda, o bot varre a janela sozinho procurando
de novo (ver `wechat_client._localizar_icone_por_tooltip`).

Uso:
    python calibrate_add_contact.py

Pra cada etapa: aperte Enter no terminal pra iniciar a contagem regressiva,
troque pro WeChat, navegue até o elemento (abrindo os popups como o fluxo
real faria) e deixe o mouse parado sobre ele até a contagem acabar — a
captura acontece sozinha nesse momento, sem precisar apertar tecla nenhuma
com o WeChat em foco (isso tiraria o foco e fecharia o popup que você
acabou de abrir).
Resultado salvo em ui_dump/add_contact_coords.json.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from config import load_config, setup_logging
from utils import (
    buscar_janela, dormir, focar_janela, geometria_janela, janela_ativa,
    posicao_mouse, titulo_janela,
)
from wechat_client import ICONE_ETAPAS, TEXTO_ETAPAS, ler_texto_no_cursor

# O WeChat só tem UMA janela de verdade (confirmado ao vivo via
# _NET_CLIENT_LIST) — busca, perfil e pedido de amizade são tudo desenhado
# dentro dela, não em popups separados. Por isso capturamos sempre por
# `window_id` direto (a captura em si já é por geometria conhecida, não por
# "janela ativa" — ver wechat_client._capturar_janela). `janela_ativa()` só
# entra aqui como diagnóstico (avisar se o foco não estava no WeChat).

CONTAGEM_SEGUNDOS = 5

logger = logging.getLogger(__name__)

OUT_PATH = Path("ui_dump/add_contact_coords.json")

DESCRICOES = {
    "shortcuts_button": "o botão de atalhos (ícone, sem texto)",
    "add_contact_button": "o botão de add contact",
    "phone_input_field": "a barra de inserir número",
    "add_to_contacts_button": "o botão 'Adicionar aos contatos' / 'Add to Contacts' no perfil aberto",
    "send_request_button": "o botão de confirmar/enviar o pedido de amizade",
}

ETAPAS = [(chave, DESCRICOES[chave]) for chave in (*ICONE_ETAPAS, *TEXTO_ETAPAS)]


def _contagem_regressiva(segundos: int) -> None:
    for restante in range(segundos, 0, -1):
        sys.stdout.write(f"\r   capturando em {restante}s... (deixe o mouse parado)   ")
        sys.stdout.flush()
        dormir(1)
    sys.stdout.write("\r   capturando agora...                                        \n")
    sys.stdout.flush()


def _capturar_etapa(chave: str, window_id: str) -> dict:
    geom = geometria_janela(window_id)
    x, y = posicao_mouse()
    rel = [x - geom["x"], y - geom["y"]]
    # mover=False: o cursor real do usuário já está exatamente aqui —
    # reposicionar via ydotool é desnecessário e arriscado (ver docstring
    # de ler_texto_no_cursor: o mapeamento --absolute entre monitores tem
    # bug conhecido e já jogou o cursor pro lugar errado bem na hora da
    # captura). focar=False: a captura já é por geometria conhecida
    # (spectacle -f + recorte), não precisa reativar nada.
    texto = ler_texto_no_cursor(window_id, x, y, mover=False, focar=False).strip()

    if chave in ICONE_ETAPAS:
        print(f"   {chave} = pos={rel} tooltip={texto!r}\n")
        return {"pos": rel, "tooltip": texto}

    if not texto:
        print(
            f"   AVISO: nenhum texto lido perto do cursor pra '{chave}'. "
            f"Confirme que o mouse estava bem em cima do rótulo.\n"
        )
    else:
        print(f"   {chave} = texto={texto!r}\n")
    return {"texto": texto}


def main() -> None:
    config = load_config()
    setup_logging(config.log_level)

    window_id = buscar_janela(config.window_name)
    if not window_id:
        raise RuntimeError(
            f"Janela '{config.window_name}' não encontrada. O WeChat está aberto?"
        )

    focar_janela(window_id)
    print(
        "Pra cada etapa: aperte Enter aqui pra iniciar a contagem, troque "
        "pro WeChat, navegue até a tela certa (abrindo os popups como o "
        "fluxo real faria) e deixe o mouse parado sobre o elemento até a "
        "contagem acabar.\n"
    )

    alvos_titulo = [alt.lower() for alt in config.window_name.split("|") if alt]

    coords: dict[str, dict] = {}
    for chave, descricao in ETAPAS:
        print(f"-> Próxima etapa: {descricao}.")
        input("   Enter pra iniciar a contagem... ")
        _contagem_regressiva(CONTAGEM_SEGUNDOS)

        # Diagnóstico: a captura em si não depende mais de foco (usa
        # geometria conhecida), mas se o foco real não estava no WeChat
        # nesse instante, é bom sinal de que você não deu tempo de navegar
        # até a tela certa antes da contagem acabar.
        ativa = janela_ativa()
        titulo = titulo_janela(ativa).lower() if ativa else ""
        if ativa and titulo and not any(alvo in titulo for alvo in alvos_titulo):
            print(
                f"   AVISO: o foco no momento da captura estava em "
                f"{titulo_janela(ativa)!r}, não no WeChat. Talvez não deu "
                f"tempo de navegar até a tela certa — considere repetir "
                f"esta etapa.\n"
            )

        coords[chave] = _capturar_etapa(chave, window_id)

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(coords, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Salvo em {OUT_PATH}. Essas coordenadas já são usadas por wechat_client.py.")


if __name__ == "__main__":
    main()
