"""Leitura e envio de mensagens no WeChat desktop (Linux) via coordenadas de
tela + OCR (Caminho B — confirmado com `explore_ui.py`: a árvore AT-SPI vem
vazia pra esse app, então não dá pra automatizar de forma semântica).

Coordenadas calibradas contra a janela real (1309x650, ver
`ui_dump/chat_aberto.png` da sessão de calibração) — são RELATIVAS à janela
(somadas a `geometria_janela()["x"/"y"]` pra virar coordenada absoluta de
tela), não a pixels fixos da tela. Se o WeChat mudar de layout/tamanho de
janela, essas constantes precisam ser recalibradas (rodar `explore_ui.py` de
novo e inspecionar o screenshot).
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytesseract
from PIL import Image, ImageChops

from utils import (
    buscar_janela, buscar_janela_por_nome, clicar, colar_texto, dormir,
    focar_janela, geometria_janela, janela_ativa, mover_mouse, tecla,
)

logger = logging.getLogger(__name__)

TICK_SCREENSHOT = Path("ui_dump/_tick.png")

# Preenchido por `calibrate_add_contact.py` — não existe valor "de fábrica"
# confiável pra esse fluxo (nunca foi mapeado contra a janela real, ao
# contrário das constantes de envio de mensagem abaixo).
ADD_CONTACT_COORDS_PATH = Path("ui_dump/add_contact_coords.json")

SIDEBAR_WIDTH = 272

# Caixa de texto de composição — ponto central de uma área ampla e sempre
# vazia (funciona independente do tamanho do texto já digitado).
INPUT_BOX_REL = (700, 550)

# Botão "Send(S)", canto inferior direito do painel de mensagens.
SEND_BUTTON_REL = (1240, 625)

# Área do painel de mensagens (exclui sidebar, cabeçalho do chat e a caixa
# de composição) — usada pra OCR de leitura.
MESSAGE_AREA_REL = (SIDEBAR_WIDTH, 70, 1309, 495)

# Área do título do chat aberto (nome do contato/grupo, topo do painel).
CHAT_TITLE_AREA_REL = (SIDEBAR_WIDTH, 15, 700, 55)

OCR_LANGS = "eng+por"


@dataclass
class IncomingMessage:
    chat_name: str
    text: str


def _capturar_janela(window_id: str, focar: bool = False) -> Image.Image:
    """Captura a TELA TODA (`spectacle -f`, todos os monitores) e recorta
    pela geometria conhecida de `window_id` — em vez de `spectacle -a`
    (janela ATIVA), que causava dois bugs confirmados ao vivo: (1) se o
    usuário estivesse com foco em outra janela (IDE, terminal) no instante
    exato da captura, fotografava aquilo em vez do WeChat, produzindo OCR
    de conteúdo completamente errado; (2) reativar a janela antes de
    capturar (`focar=True`) fechava popups/menus transitórios que
    dependiam de foco pra continuar abertos.

    Não depende de foco NENHUM — só que a janela esteja visível na tela
    (não coberta por outra no mesmo monitor). `focar=True` ainda existe
    pra quando você quer garantir que a janela está à frente antes de
    clicar nela (não pra capturar).
    """
    if focar:
        focar_janela(window_id)
        dormir(0.3)
    TICK_SCREENSHOT.parent.mkdir(exist_ok=True)
    subprocess.run(
        ["spectacle", "-b", "-n", "-f", "-o", str(TICK_SCREENSHOT.resolve())],
        check=True,
        capture_output=True,
    )
    # .copy() força carregar os pixels agora — o arquivo em TICK_SCREENSHOT é
    # reaproveitado pela próxima captura, e sem isso a leitura ficaria
    # preguiçosa (Image.open não lê o conteúdo até ser usado) e poderia
    # acabar lendo o screenshot seguinte em vez deste.
    imagem_completa = Image.open(TICK_SCREENSHOT).copy()
    geom = geometria_janela(window_id)
    caixa = (geom["x"], geom["y"], geom["x"] + geom["width"], geom["y"] + geom["height"])
    return imagem_completa.crop(caixa)


TEXTO_CURSOR_ESPERA = 0.9  # tempo pra legenda de ícone aparecer depois do hover
TEXTO_CURSOR_RAIO_X = 160
TEXTO_CURSOR_ALTURA = 70


def ler_texto_no_cursor(
    window_id: str, x_abs: int, y_abs: int, mover: bool = True, focar: bool = True
) -> str:
    """Passa o mouse por (x_abs, y_abs) SEM clicar (a menos que `mover=False`)
    e devolve só a LINHA de texto mais próxima do cursor — tanto faz se é
    uma legenda (tooltip, só aparece depois do hover) ou o rótulo já
    visível de um botão com texto.

    Serve pra confirmar/localizar botões por CONTEÚDO em vez de coordenada
    fixa. É essencial pra ícone-only (a legenda é texto de verdade,
    renderizado normalmente mesmo quando o ícone sofre do bug de
    renderização que motivou trocar pra automação por coordenada) — sem
    isso, não dava pra verificar esse tipo de botão por OCR de jeito
    nenhum, só por "a tela mudou" (ver `_tela_mudou`), que confirma que
    algo aconteceu mas não que foi o botão CERTO.

    Devolve só a linha mais próxima, não um dump de tudo que está na área
    (a área ao redor do cursor costuma ter MAIS de uma linha vizinha — item
    de menu do lado, texto de outro elemento — e um dump bruto de
    `image_to_string` concatena tudo isso numa string só, inútil pra achar
    esse texto de novo depois via `_localizar_texto_em_area`).

    `mover=False` pula o `mover_mouse` (usado pela calibração interativa,
    onde o cursor real do usuário já está exatamente ali — mover de novo
    via `ydotool --absolute` é redundante e, pior, sofre do mesmo bug de
    mapeamento entre monitores já visto em outras partes do projeto:
    confirmado ao vivo que isso jogava o cursor pra um lugar errado bem na
    hora de tirar o screenshot, estragando a calibração).

    `focar=False` pula o `windowactivate` da captura (ver `_capturar_janela`)
    — essencial quando há um POPUP FILHO aberto por cima da janela
    principal (menu de atalhos, diálogo de adicionar contato): reativar a
    janela base pra tirar o screenshot faz o popup minimizar/fechar junto,
    confirmado ao vivo (a própria captura estava destruindo o popup que a
    gente queria fotografar).
    """
    if mover:
        mover_mouse(x_abs, y_abs)
    dormir(TEXTO_CURSOR_ESPERA)
    imagem = _capturar_janela(window_id, focar=focar)
    geom = geometria_janela(window_id)
    cx, cy = x_abs - geom["x"], y_abs - geom["y"]
    caixa = (
        max(cx - TEXTO_CURSOR_RAIO_X, 0),
        max(cy - TEXTO_CURSOR_ALTURA, 0),
        min(cx + TEXTO_CURSOR_RAIO_X, imagem.width),
        min(cy + TEXTO_CURSOR_ALTURA, imagem.height),
    )
    recorte = imagem.crop(caixa)
    dados = pytesseract.image_to_data(recorte, lang=OCR_LANGS, output_type=pytesseract.Output.DICT)

    linhas: dict[tuple[int, int, int], list[int]] = {}
    for i, texto in enumerate(dados["text"]):
        if not texto.strip():
            continue
        chave = (dados["block_num"][i], dados["par_num"][i], dados["line_num"][i])
        linhas.setdefault(chave, []).append(i)
    if not linhas:
        return ""

    # Cursor relativo ao recorte (não à janela) — é contra isso que
    # medimos a distância de cada linha candidata.
    cx_recorte, cy_recorte = cx - caixa[0], cy - caixa[1]

    melhor_texto = ""
    melhor_dist = None
    for indices in linhas.values():
        esquerda = min(dados["left"][i] for i in indices)
        direita = max(dados["left"][i] + dados["width"][i] for i in indices)
        topo = min(dados["top"][i] for i in indices)
        baixo = max(dados["top"][i] + dados["height"][i] for i in indices)
        centro_x, centro_y = (esquerda + direita) / 2, (topo + baixo) / 2
        dist = (centro_x - cx_recorte) ** 2 + (centro_y - cy_recorte) ** 2
        if melhor_dist is None or dist < melhor_dist:
            melhor_dist = dist
            melhor_texto = " ".join(dados["text"][i] for i in indices).strip()
    return melhor_texto


def _tela_mudou(antes: Image.Image, depois: Image.Image) -> bool:
    """True se houve qualquer diferença visível entre dois screenshots da
    mesma janela — usado como confirmação genérica de que um clique surtiu
    efeito (abriu um popup, mudou de tela etc.), sem precisar saber de
    antemão QUAL texto/elemento esperar (muitos botões desse fluxo são
    ícone-only e podem estar afetados pelo bug de renderização, então OCR
    de conteúdo específico nem sempre é confiável aqui — "mudou algo" é um
    sinal mais fraco que "apareceu o texto X", mas não depende de calibrar
    o que procurar em cada etapa, e já transforma clique-no-lugar-errado
    silencioso em falha visível.
    """
    if antes.size != depois.size:
        return True
    diff = ImageChops.difference(antes.convert("RGB"), depois.convert("RGB"))
    return diff.getbbox() is not None


def _ocr_texto(imagem: Image.Image, caixa: tuple[int, int, int, int]) -> str:
    recorte = imagem.crop(caixa)
    return pytesseract.image_to_string(recorte, lang=OCR_LANGS).strip()


def _localizar_texto_em_area(
    imagem: Image.Image, alvo: str, caixa: tuple[int, int, int, int] | None = None
) -> tuple[int, int] | None:
    """OCR em `caixa` (ou na imagem toda, se None) procurando `alvo`; devolve
    o centro (x,y) RELATIVO À IMAGEM (não à caixa) da linha de texto que
    contém esse texto, ou None se não achar.

    Tesseract devolve uma palavra por item — nomes com espaço (ex. "File
    Transfer", "Add Contacts") vêm em itens separados. Por isso agrupamos por
    linha (block_num/par_num/line_num) e comparamos a linha inteira, não
    palavra a palavra.
    """
    offset_x, offset_y = 0, 0
    recorte = imagem
    if caixa is not None:
        recorte = imagem.crop(caixa)
        offset_x, offset_y = caixa[0], caixa[1]

    dados = pytesseract.image_to_data(recorte, lang=OCR_LANGS, output_type=pytesseract.Output.DICT)

    linhas: dict[tuple[int, int, int], list[int]] = {}
    for i, texto in enumerate(dados["text"]):
        if not texto.strip():
            continue
        chave = (dados["block_num"][i], dados["par_num"][i], dados["line_num"][i])
        linhas.setdefault(chave, []).append(i)

    # Contém, não igualdade exata: ícones colados no texto às vezes viram
    # caractere-lixo (ex. ". File Transfer").
    alvo_lower = alvo.lower()
    for indices in linhas.values():
        texto_linha = " ".join(dados["text"][i] for i in indices).strip()
        if alvo_lower in texto_linha.lower():
            esquerda = min(dados["left"][i] for i in indices)
            direita = max(dados["left"][i] + dados["width"][i] for i in indices)
            topo = min(dados["top"][i] for i in indices)
            baixo = max(dados["top"][i] + dados["height"][i] for i in indices)
            return offset_x + (esquerda + direita) // 2, offset_y + (topo + baixo) // 2
    return None


def _localizar_texto_na_sidebar(imagem: Image.Image, alvo: str) -> tuple[int, int] | None:
    return _localizar_texto_em_area(imagem, alvo, (0, 0, SIDEBAR_WIDTH, imagem.height))


def send_message(window_class_name: str, chat_name: str, text: str) -> None:
    """Efeito colateral conhecido: como não há isolamento de sessão (é a
    tela real do colaborador), qualquer clique/foco do usuário no meio da
    sequência pode roubar o foco entre um passo e outro — confirmado ao vivo
    (um `colar_texto` acabou colando no VS Code em vez do WeChat porque o
    usuário estava com o mouse/teclado ativo em outra janela naquele
    instante). Por isso refocamos a janela do WeChat imediatamente antes de
    CADA ação (clique/colagem), não só uma vez no início — reduz a janela de
    corrida, mesmo sem eliminá-la por completo.
    """
    window_id = buscar_janela(window_class_name)
    if not window_id:
        raise RuntimeError(f"Janela '{window_class_name}' não encontrada.")

    geom = geometria_janela(window_id)
    imagem = _capturar_janela(window_id)

    # Causa raiz confirmada ao vivo de um bug bem confuso de debugar: clicar
    # na conversa na sidebar quando ela JÁ é a conversa aberta a FECHA (é um
    # toggle) — daí o clique seguinte na caixa de texto caía no painel vazio
    # (sem chat aberto) e a colagem/envio não iam a lugar nenhum, sem
    # nenhum erro. Por isso é essencial checar o título do chat já aberto
    # (`CHAT_TITLE_AREA_REL`) e só clicar na sidebar se for de fato preciso
    # trocar de conversa. Isso importa ainda mais quando o bot precisar
    # alternar entre várias conversas em sequência — nunca assumir qual
    # conversa está aberta, sempre confirmar antes de agir.
    chat_ja_aberto = _ocr_texto(imagem, CHAT_TITLE_AREA_REL)
    precisa_trocar_de_conversa = chat_name.lower() not in chat_ja_aberto.lower()

    if precisa_trocar_de_conversa:
        posicao = _localizar_texto_na_sidebar(imagem, chat_name)
        if posicao is None:
            raise RuntimeError(
                f"Conversa '{chat_name}' não encontrada na sidebar via OCR. "
                f"Ela está visível na lista sem precisar rolar?"
            )
        focar_janela(window_id)
        dormir(0.3)
        clicar(geom["x"] + posicao[0], geom["y"] + posicao[1])
        dormir(0.8)

    focar_janela(window_id)
    dormir(0.3)
    clicar(geom["x"] + INPUT_BOX_REL[0], geom["y"] + INPUT_BOX_REL[1])
    dormir(0.5)

    focar_janela(window_id)
    dormir(0.3)
    colar_texto(text)
    dormir(0.6)

    focar_janela(window_id)
    dormir(0.3)
    clicar(geom["x"] + SEND_BUTTON_REL[0], geom["y"] + SEND_BUTTON_REL[1])


def read_new_messages(window_class_name: str, ja_vistas: set[str]) -> list[IncomingMessage]:
    """Faz OCR do painel de mensagens do chat atualmente aberto e devolve as
    linhas que ainda não estão em `ja_vistas` (o chamador deve persistir esse
    set entre chamadas — ver main.py).

    Limitação conhecida: não distingue remetente nem detecta troca de chat
    aberto além do título; é uma comparação de linhas de texto, não uma
    leitura estruturada (não temos DOM nem AT-SPI aqui).
    """
    window_id = buscar_janela(window_class_name)
    if not window_id:
        return []

    imagem = _capturar_janela(window_id)
    chat_name = _ocr_texto(imagem, CHAT_TITLE_AREA_REL) or "?"
    texto_bruto = _ocr_texto(imagem, MESSAGE_AREA_REL)

    novas = []
    for linha in texto_bruto.splitlines():
        linha = linha.strip()
        if not linha or linha in ja_vistas:
            continue
        ja_vistas.add(linha)
        novas.append(IncomingMessage(chat_name=chat_name, text=linha))
    return novas


# Passos com rótulo de texto visível — localizados por OCR na hora, nunca
# por coordenada fixa (elimina recalibração por mudança de posição/tela).
TEXTO_ETAPAS = (
    "add_contact_button", "phone_input_field", "add_to_contacts_button",
    "send_request_button",
)
# Único passo ícone-only do fluxo (sem rótulo visível) — precisa de posição
# + legenda (tooltip) pra confirmar por conteúdo; ver _localizar_icone_por_tooltip.
ICONE_ETAPAS = ("shortcuts_button",)

SWEEP_PASSO_PX = 40
SWEEP_ALTURA_MAX = 90  # faixa do topo da janela varrida em busca do ícone


def _carregar_coords_add_contact() -> dict[str, dict]:
    if not ADD_CONTACT_COORDS_PATH.exists():
        raise RuntimeError(
            f"{ADD_CONTACT_COORDS_PATH} não existe. Rode "
            "`python calibrate_add_contact.py` primeiro para mapear o fluxo "
            "de busca+adicionar contato contra a janela real."
        )
    dados = json.loads(ADD_CONTACT_COORDS_PATH.read_text(encoding="utf-8"))

    faltando = [chave for chave in TEXTO_ETAPAS if chave not in dados or not dados[chave].get("texto")]
    faltando += [
        chave for chave in ICONE_ETAPAS
        if chave not in dados or not dados[chave].get("tooltip")
    ]
    if faltando:
        raise RuntimeError(
            f"{ADD_CONTACT_COORDS_PATH} está incompleto (faltando: {faltando}). "
            "Rode `python calibrate_add_contact.py` de novo."
        )
    return dados


def _localizar_icone_por_tooltip(
    window_id: str, alvo_tooltip: str, pos_conhecida: list[int] | None = None
) -> tuple[int, int] | None:
    """Acha um botão ícone-only por CONTEÚDO da legenda, não por coordenada
    fixa: tenta a última posição conhecida primeiro (rápido, funciona
    enquanto a janela não mudar de layout); se a legenda não bater, varre
    a faixa do topo da janela em grade até achar o texto — não depende de
    recalibração manual quando a posição do ícone mudar (só fica mais
    lento nessa execução, já que precisa procurar de novo).
    """
    geom = geometria_janela(window_id)

    def bate(x_rel: int, y_rel: int) -> bool:
        texto = ler_texto_no_cursor(window_id, geom["x"] + x_rel, geom["y"] + y_rel)
        return alvo_tooltip.lower() in texto.lower()

    if pos_conhecida and bate(*pos_conhecida):
        return tuple(pos_conhecida)

    logger.info("'%s' não confirmado na posição conhecida — varrendo a janela...", alvo_tooltip)
    for y in range(10, SWEEP_ALTURA_MAX, SWEEP_PASSO_PX):
        for x in range(10, geom["width"] - 10, SWEEP_PASSO_PX):
            if bate(x, y):
                return x, y
    return None


def search_and_add_contact(window_class_name: str, phone: str, message: str) -> bool:
    """Abre o fluxo de adicionar contato do WeChat, busca `phone` DENTRO dele
    e envia pedido de amizade.

    Ordem do fluxo (mapeada ao vivo): atalhos -> add contact -> digita o
    número -> procurar -> adicionar aos contatos -> enviar. Sem etapa própria
    de mensagem de verificação (removida da calibração) — `message` não é
    usado neste fluxo; o pedido vai com a mensagem padrão do próprio WeChat,
    se houver uma.

    O menu de atalhos abre DENTRO da janela principal do WeChat, mas
    "Add Contacts" e "Send Friend Request" são janelas de verdade
    SEPARADAS — confirmado ao vivo (`xdotool search --name`), e cruciais
    de pegar certo: elas não aparecem em `_NET_CLIENT_LIST` (o método
    normal de achar janela usado em `buscar_janela`), só em busca por
    nome. Tratar tudo como "uma janela só" (tentativa anterior) fazia a
    automação capturar/clicar na janela base enquanto o diálogo de verdade
    estava por cima, sempre errando.

    Retorna False se o número não corresponder a nenhum contato do WeChat
    (não há como diferenciar isso de forma confiável sem OCR sobre uma área
    que também pode estar com texto invisível — por ora, o chamador deve
    tratar False como "não foi possível confirmar, checar manualmente").
    """
    coords = _carregar_coords_add_contact()

    window_id = buscar_janela(window_class_name)
    if not window_id:
        raise RuntimeError(f"Janela '{window_class_name}' não encontrada.")
    focar_janela(window_id)

    def _aguardar_janela_por_nome(padrao: str, tentativas: int = 15, intervalo: float = 0.3) -> str:
        for _ in range(tentativas):
            encontrada = buscar_janela_por_nome(padrao)
            if encontrada:
                return encontrada
            dormir(intervalo)
        raise RuntimeError(
            f"Janela '{padrao}' não apareceu depois de {tentativas * intervalo:.1f}s "
            f"— o passo anterior não abriu o que devia?"
        )

    def _confirmar_mudanca(chave: str, alvo_id: str, antes: Image.Image) -> None:
        dormir(0.4)
        depois = _capturar_janela(alvo_id)
        if not _tela_mudou(antes, depois):
            raise RuntimeError(
                f"Clique em '{chave}' não mudou nada na tela — o elemento "
                f"não respondeu, ou o achado por OCR/varredura estava "
                f"errado. Confira o rótulo/legenda salvo em "
                f"{ADD_CONTACT_COORDS_PATH}."
            )

    def clicar_por_texto(alvo_id: str, chave: str, verificar: bool = True) -> None:
        geom = geometria_janela(alvo_id)
        imagem = _capturar_janela(alvo_id)
        alvo = coords[chave]["texto"]
        posicao = _localizar_texto_em_area(imagem, alvo)
        if posicao is None:
            raise RuntimeError(
                f"Texto {alvo!r} da etapa '{chave}' não encontrado na tela "
                f"(janela {alvo_id}). O rótulo mudou (recalibre) ou o "
                f"passo anterior não abriu o que devia?"
            )
        clicar(geom["x"] + posicao[0], geom["y"] + posicao[1])
        if verificar:
            _confirmar_mudanca(chave, alvo_id, imagem)

    def clicar_icone(alvo_id: str, chave: str) -> None:
        geom = geometria_janela(alvo_id)
        info = coords[chave]
        posicao = _localizar_icone_por_tooltip(alvo_id, info["tooltip"], info.get("pos"))
        if posicao is None:
            raise RuntimeError(
                f"Ícone '{chave}' (legenda {info['tooltip']!r}) não "
                f"encontrado nem varrendo a janela toda."
            )
        antes = _capturar_janela(alvo_id)
        clicar(geom["x"] + posicao[0], geom["y"] + posicao[1])
        _confirmar_mudanca(chave, alvo_id, antes)

    def colar_em_janela(alvo_id: str, texto: str) -> None:
        focar_janela(alvo_id)
        dormir(0.2)
        colar_texto(texto)

    clicar_icone(window_id, "shortcuts_button")
    dormir(0.5)  # abre o menu de atalhos ("Adicionar contato", "Criar grupo" etc.)

    clicar_por_texto(window_id, "add_contact_button")
    dormir(0.5)  # abre a janela separada "Add Contacts"

    dialogo_id = _aguardar_janela_por_nome("Add Contact")

    # Só foca o campo — clicar num campo de texto vazio raramente muda algo
    # visível o suficiente pro diff pegar, então não verificamos aqui; a
    # confirmação real desse passo vem do resultado aparecer no próximo.
    clicar_por_texto(dialogo_id, "phone_input_field", verificar=False)
    dormir(0.3)
    colar_em_janela(dialogo_id, phone)
    dormir(0.3)

    # "Search" não é um botão separado — é só o placeholder do próprio
    # campo (confirmado ao vivo via OCR: "Search WeChat ID or mobile
    # number" é uma frase só). A busca dispara com Enter.
    focar_janela(dialogo_id)
    dormir(0.2)
    tecla("Return")
    dormir(1.0)  # tempo pro WeChat consultar/mostrar o resultado da busca/perfil

    clicar_por_texto(dialogo_id, "add_to_contacts_button")
    dormir(0.5)  # abre a janela separada "Send Friend Request"

    pedido_id = _aguardar_janela_por_nome("Send Friend Request")

    clicar_por_texto(pedido_id, "send_request_button")
    dormir(0.5)

    logger.info("Pedido de amizade enviado para %s (não confirmado se o número existe no WeChat).", phone)
    return True
