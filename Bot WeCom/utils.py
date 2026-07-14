"""Wrappers finos sobre `xdotool`/`xclip` (automação X11) + sleep/jitter.

O WeChat desktop (wechat-bin) roda como cliente X11 via XWayland
(QT_QPA_PLATFORM=xcb, confirmado no sandbox config) — por isso ferramentas
X11 alcançam a janela mesmo numa sessão Wayland.
"""

from __future__ import annotations

import logging
import random
import re
import subprocess
import time

logger = logging.getLogger(__name__)


def dormir(segundos: float) -> None:
    time.sleep(segundos)


def aleatorio(minimo: float, maximo: float) -> float:
    return minimo + random.random() * (maximo - minimo)


def _run(cmd: list[str]) -> str:
    resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return resultado.stdout.strip()


def buscar_janela(window_name: str) -> str | None:
    """Retorna o id (decimal) da janela de topo cujo título contém
    `window_name` (case-insensitive) — ou, se `window_name` tiver `|`,
    qualquer uma das alternativas —, ou None se não encontrar.

    O título da janela principal do wechat-bin varia entre sessões ("Weixin"
    numa, "WeChat" noutra, confirmado ao vivo) — por isso o valor padrão em
    `config.py` é "WeChat|Weixin".

    Nem `xdotool search --class` nem `--name` são confiáveis aqui: --class
    "wechat" casa com sub-janelas minúsculas (tooltip, ícone de bandeja —
    confirmado ao vivo, uma de 223x208 veio antes da janela real de
    1309x650); e --name com regex livre casa "WeChat" dentro de
    "WeChatAppEx" (janela auxiliar de mini-programas) e ainda pode achar
    mais de uma janela com título idêntico (o título mudou de "Weixin" pra
    "WeChat" entre uma sessão e outra do mesmo app — não é estável).

    Por isso filtramos pelas janelas listadas em `_NET_CLIENT_LIST` da raiz
    — só janelas de topo de verdade, gerenciadas pelo window manager,
    excluindo tooltips/popups/janelas auxiliares — e comparamos o título
    exato dessas.
    """
    try:
        saida_raiz = _run(["xprop", "-root", "_NET_CLIENT_LIST"])
    except subprocess.CalledProcessError:
        return None

    ids_hex = re.findall(r"0x[0-9a-fA-F]+", saida_raiz)
    alvos = [alt.lower() for alt in window_name.split("|") if alt]
    for id_hex in ids_hex:
        try:
            saida_nome = _run(["xprop", "-id", id_hex, "_NET_WM_NAME"])
        except subprocess.CalledProcessError:
            continue
        nome_lower = saida_nome.lower()
        if any(alvo in nome_lower for alvo in alvos):
            return str(int(id_hex, 16))
    return None


def geometria_janela(window_id: str) -> dict:
    """Retorna {"x":..,"y":..,"width":..,"height":..} da janela via xdotool."""
    saida = _run(["xdotool", "getwindowgeometry", "--shell", window_id])
    dados = {}
    for linha in saida.splitlines():
        chave, _, valor = linha.partition("=")
        if chave in ("X", "Y", "WIDTH", "HEIGHT"):
            dados[chave.lower()] = int(valor)
    return dados


def focar_janela(window_id: str) -> None:
    # Sem "--sync": no KWin/Wayland esse flag pode nunca receber a
    # confirmação esperada e travar indefinidamente (visto ao vivo). Um
    # `dormir()` curto depois de chamar essa função é suficiente.
    _run(["xdotool", "windowactivate", window_id])


def clicar(x: int, y: int) -> None:
    # Evitar "--sync" aqui também, pelo mesmo motivo do focar_janela.
    _run(["xdotool", "mousemove", str(x), str(y)])
    dormir(0.1)
    _run(["xdotool", "click", "1"])


def colar_texto(texto: str) -> None:
    """Copia `texto` pro clipboard (via xclip) e cola com Ctrl+V — mais
    confiável que `xdotool type` pra acentos/unicode.
    """
    subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input=texto,
        text=True,
        check=True,
    )
    _run(["xdotool", "key", "ctrl+v"])


def tecla(nome: str) -> None:
    _run(["xdotool", "key", nome])
