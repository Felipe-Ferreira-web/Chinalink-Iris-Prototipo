"""Automação mínima do WeChat via pywinauto, em cima de seletores REAIS
inspecionados com inspect_ui.py (ver ui_dump.txt) — não adivinhados.

Cobre só o que o Iris precisa: abrir uma conversa, enviar mensagem, ler
mensagens. Não tenta replicar a API inteira de um "wxauto" (ver README,
seção "Tentativa abandonada").

Seletores confirmados no dump real:
- Item de conversa na sidebar: auto_id='session_item_<Nome>', dentro da
  lista auto_id='session_list'.
- Campo de digitar mensagem: auto_id='chat_input_field' (Edit).
- Botão de enviar: text='Send' (classe mmui::XOutlineButton).
- Lista de mensagens: auto_id='chat_message_list'; itens de texto são
  class='mmui::ChatTextItemView' (outros tipos, ex. ChatItemView, são só
  separador de horário, sem conteúdo de mensagem).

Fluxo de adicionar contato (janelas separadas de verdade, confirmado nos
dumps `ui_dump_add_contact.txt`/`ui_dump_send_friend_request.txt`):
- Diálogo "Add Contacts" (class mmui::AddFriendWindow): campo de busca é
  o único Edit da janela; botão "Search" de verdade (title='Search',
  diferente da busca da sidebar, que usa Enter); resultado "não
  encontrado" é um Text contendo "User not found"; resultado encontrado
  mostra um botão title='Add to Contacts'.
- Diálogo "Send Friend Request" (class mmui::VerifyFriendWindow): campo
  de mensagem de verificação é um Edit (pré-preenchido, editável); botão
  de confirmar é title='OK' (existe também title='Cancel' — desambiguar
  sempre pelo texto).
"""

from __future__ import annotations

import time

import win32clipboard
import win32con
from pywinauto import Desktop

TITLE_NEEDLES = ("Weixin", "WeChat", "微信")
# Classes de janela de outros apps que só coincidem no título (ex.: uma aba
# do navegador com "微信" no texto) — nunca é a janela real do WeChat.
FALSE_POSITIVE_CLASS_PREFIXES = ("Chrome_WidgetWin",)
MESSAGE_TEXT_CLASS = "mmui::ChatTextItemView"
SESSION_ITEM_PREFIX = "session_item_"
CURRENT_CHAT_LABEL_SUFFIX = "current_chat_name_label"
ADD_CONTACTS_MENU_TEXT = "Add Contacts"
ADD_CONTACTS_WINDOW_TITLE = ("Add Contacts",)
SEND_FRIEND_REQUEST_WINDOW_TITLE = ("Send Friend Request",)
USER_NOT_FOUND_TEXT = "User not found"
# Esse servidor é lento pra chamadas UIA (achar a janela chegou a levar 1
# minuto) — timeout generoso, com retry, em vez de assumir que o elemento
# já está renderizado logo após uma ação (click, troca de chat etc).
FIND_TIMEOUT_SECONDS = 15.0
FIND_POLL_INTERVAL_SECONDS = 0.5


def find_window_by_title(
    title_needles: tuple[str, ...],
    filter_false_positives: bool = False,
    timeout: float = FIND_TIMEOUT_SECONDS,
):
    """Acha uma janela de nível superior pelo título, com retry até `timeout`
    — útil tanto pra janela principal (já aberta) quanto pra diálogos que só
    aparecem depois de um clique (ex.: "Add Contacts", "Send Friend Request").
    """
    deadline = time.monotonic() + timeout
    while True:
        desktop = Desktop(backend="uia")
        candidates = []
        for window in desktop.windows():
            try:
                title = window.window_text()
                class_name = window.element_info.class_name
            except Exception:
                continue
            if not any(needle in title for needle in title_needles):
                continue
            if filter_false_positives and any(
                class_name.startswith(prefix) for prefix in FALSE_POSITIVE_CLASS_PREFIXES
            ):
                continue
            candidates.append(window)
        candidates.sort(key=lambda w: 0 if w.element_info.class_name.startswith("mmui") else 1)
        if candidates:
            return candidates[0]
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"Nenhuma janela com título contendo {title_needles!r} encontrada "
                f"após {timeout}s."
            )
        time.sleep(FIND_POLL_INTERVAL_SECONDS)


def find_wechat_window():
    return find_window_by_title(TITLE_NEEDLES, filter_false_positives=True)


def _find_one(
    window,
    error_label: str,
    auto_id: str | None = None,
    timeout: float = FIND_TIMEOUT_SECONDS,
    **kwargs,
):
    # pywinauto 0.6.9 não aceita auto_id= como filtro direto em
    # descendants()/children() (só class_name/title/control_type são
    # repassados pra build_condition) — filtra auto_id na mão em Python.
    #
    # Tenta de novo até `timeout` em vez de olhar uma vez só: o servidor é
    # lento pra chamadas UIA, e um elemento pode ainda não estar renderizado
    # logo após uma ação (clique, troca de chat).
    deadline = time.monotonic() + timeout
    while True:
        matches = window.descendants(**kwargs)
        if auto_id is not None:
            matches = [m for m in matches if m.element_info.automation_id == auto_id]
        if matches:
            return matches[0]
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"{error_label} não encontrado após {timeout}s (auto_id={auto_id!r}, {kwargs})."
            )
        time.sleep(FIND_POLL_INTERVAL_SECONDS)


def _set_clipboard_text(text: str) -> None:
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()


def list_sessions(window) -> list[str]:
    session_list = _find_one(window, "Lista de conversas", auto_id="session_list")
    names = []
    for item in session_list.children(control_type="ListItem"):
        auto_id = item.element_info.automation_id
        if auto_id.startswith(SESSION_ITEM_PREFIX):
            names.append(auto_id[len(SESSION_ITEM_PREFIX):])
    return names


def get_current_chat_name(window) -> str | None:
    for item in window.descendants(control_type="Text"):
        if item.element_info.automation_id.endswith(CURRENT_CHAT_LABEL_SUFFIX):
            return item.window_text()
    return None


def _focus_window(window) -> None:
    # click_input() faz um clique de mouse de verdade nas coordenadas de
    # tela — sem trazer a janela pra frente antes (só faz isso sozinho se
    # for um diálogo). Se o WeChat não estiver em primeiro plano (ex.: o
    # terminal rodando este script está por cima), o clique cai no que
    # estiver visível ali, não no WeChat. Refoca antes de CADA ação.
    window.set_focus()
    time.sleep(0.3)


def _click_by_text(text: str, timeout: float = FIND_TIMEOUT_SECONDS) -> None:
    """Clica no primeiro elemento com esse texto em QUALQUER janela de nível
    superior — usado pra item de menu/popup transitório (ex.: o menu de
    atalhos), cuja janela não tem título/classe estável pra buscar direto
    (o próprio dump confirma que popups do WeChat são janelas de nível
    superior de verdade, não filhas da janela principal).
    """
    deadline = time.monotonic() + timeout
    while True:
        for window in Desktop(backend="uia").windows():
            try:
                matches = window.descendants(title=text)
            except Exception:
                continue
            if matches:
                matches[0].click_input()
                return
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Elemento com texto {text!r} não encontrado em nenhuma janela.")
        time.sleep(FIND_POLL_INTERVAL_SECONDS)


def open_add_contact_dialog(main_window):
    """Abre o diálogo "Add Contacts" a partir da janela principal do WeChat."""
    _focus_window(main_window)
    shortcuts_button = _find_one(
        main_window, "Botão 'Shortcuts'", title="Shortcuts", control_type="Button"
    )
    shortcuts_button.click_input()
    _click_by_text(ADD_CONTACTS_MENU_TEXT)
    return find_window_by_title(ADD_CONTACTS_WINDOW_TITLE)


def add_contact_by_phone(main_window, phone: str, message: str | None = None) -> str | None:
    """Busca `phone` no diálogo "Add Contacts" e manda pedido de amizade,
    opcionalmente customizando a mensagem de verificação.

    Retorna o APELIDO (nickname) real do WeChat da pessoa em caso de
    sucesso, ou `None` se o número não corresponder a nenhum contato —
    o nome do fornecedor no Django (ou o telefone) quase nunca bate com
    esse apelido, então é ele (não `phone`/`supplier.name`) que precisa
    ser usado depois em `send_message`/`open_chat` pra achar a conversa
    na sidebar (auto_id='session_item_<apelido>').

    Precisa da outra pessoa ACEITAR o pedido antes de existir conversa
    pra `send_message` funcionar (ver README).
    """
    dialog = open_add_contact_dialog(main_window)
    _focus_window(dialog)

    search_field = _find_one(dialog, "Campo de busca", control_type="Edit")
    search_field.click_input()
    _set_clipboard_text(phone)
    search_field.type_keys("^v", pause=0.05)
    time.sleep(0.3)

    search_button = _find_one(dialog, "Botão 'Search'", title="Search", control_type="Button")
    _focus_window(dialog)
    search_button.click_input()

    # Espera ou o card de perfil (botão "Add to Contacts") ou a mensagem
    # de "não encontrado" — o que aparecer primeiro decide o resultado.
    deadline = time.monotonic() + FIND_TIMEOUT_SECONDS
    add_button = None
    nickname = None
    while time.monotonic() < deadline:
        not_found = [
            d for d in dialog.descendants(control_type="Text")
            if USER_NOT_FOUND_TEXT in d.window_text()
        ]
        if not_found:
            return None
        found = dialog.descendants(title="Add to Contacts", control_type="Button")
        if found:
            add_button = found[0]
            nickname_matches = [
                d for d in dialog.descendants(control_type="Text")
                if d.element_info.automation_id.endswith("display_name_text")
            ]
            nickname = nickname_matches[0].window_text() if nickname_matches else None
            break
        time.sleep(FIND_POLL_INTERVAL_SECONDS)
    if add_button is None:
        raise RuntimeError(
            f"Nem resultado nem 'não encontrado' apareceu pra {phone!r} "
            f"após {FIND_TIMEOUT_SECONDS}s."
        )
    if not nickname:
        raise RuntimeError(
            f"Card de perfil encontrado pra {phone!r}, mas não achei o apelido "
            f"(display_name_text) — não dá pra saber o nome da conversa depois."
        )

    _focus_window(dialog)
    add_button.click_input()

    request_window = find_window_by_title(SEND_FRIEND_REQUEST_WINDOW_TITLE)
    _focus_window(request_window)

    if message is not None:
        message_field = _find_one(
            request_window, "Campo de mensagem do pedido", control_type="Edit"
        )
        message_field.click_input()
        message_field.type_keys("^a", pause=0.05)
        _set_clipboard_text(message)
        message_field.type_keys("^v", pause=0.05)
        time.sleep(0.3)

    ok_button = _find_one(request_window, "Botão 'OK'", title="OK", control_type="Button")
    _focus_window(request_window)
    ok_button.click_input()
    return nickname


def open_chat(window, chat_name: str) -> None:
    # Clicar numa conversa que já está aberta a FECHA (é toggle, não "abrir
    # garantido") — sempre confirma o estado atual antes de agir.
    if get_current_chat_name(window) == chat_name:
        return
    item = _find_one(
        window,
        f"Conversa '{chat_name}' na sidebar",
        auto_id=f"session_item_{chat_name}",
    )
    _focus_window(window)
    item.click_input()


def send_message(window, chat_name: str, text: str) -> None:
    open_chat(window, chat_name)
    input_field = _find_one(window, "Campo de mensagem", auto_id="chat_input_field")
    _focus_window(window)
    input_field.click_input()
    _set_clipboard_text(text)
    input_field.type_keys("^v", pause=0.05)
    time.sleep(1.0)  # servidor lento; dá tempo do paste refletir antes de enviar
    send_button = _find_one(window, "Botão 'Send'", title="Send", control_type="Button")
    _focus_window(window)
    send_button.click_input()


def read_messages(window, chat_name: str | None = None) -> list[str]:
    if chat_name:
        open_chat(window, chat_name)
    message_list = _find_one(window, "Lista de mensagens", auto_id="chat_message_list")
    texts = []
    for item in message_list.children(control_type="ListItem"):
        if item.element_info.class_name == MESSAGE_TEXT_CLASS:
            texts.append(item.window_text())
    return texts
