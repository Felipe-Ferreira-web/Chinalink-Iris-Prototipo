"""Automação do WeChat via pywinauto, sobre seletores reais confirmados
(ver docs/README.md) — conversas, mensagens, contatos, grupos, arquivos."""

from __future__ import annotations

import random
import time
from pathlib import Path

import win32clipboard
import win32con
from pywinauto import Desktop

from .setup_wechat import (
    ADD_CONTACTS_MENU_TEXT,
    ADD_CONTACTS_WINDOW_TITLE,
    CLOSE_BUTTON_TEXT,
    CONTACT_ITEM_CLASS,
    CONTACTS_TAB_TEXT,
    CURRENT_CHAT_LABEL_SUFFIX,
    DIALOG_PRIMARY_BUTTON_ID,
    DOWNLOAD_TO_MENU_PREFIX,
    FALSE_POSITIVE_CLASS_PREFIXES,
    FILE_BUBBLE_CLASS,
    FILE_NAME_FIELD_LABEL,
    FIND_POLL_INTERVAL_SECONDS,
    FIND_TIMEOUT_SECONDS,
    GROUP_CONTACT_ROW_CLASS,
    MESSAGE_TEXT_CLASS,
    MESSAGES_BUTTON_TEXT,
    NOT_DOWNLOADED_MARKER,
    REMARK_VALUE_CLASS,
    SAVE_AS_MENU_PREFIX,
    SAVE_DIALOG_WINDOW_TITLE,
    SELECT_FILE_WINDOW_TITLE,
    SEND_FILE_BUTTON_TEXT,
    SEND_FRIEND_REQUEST_WINDOW_TITLE,
    SESSION_ITEM_PREFIX,
    START_GROUP_CHAT_MENU_TEXT,
    START_GROUP_CHAT_WINDOW_TITLE,
    TITLE_NEEDLES,
    UNREAD_MARKER_RE,
    USER_NOT_FOUND_TEXT,
    WEIXIN_TAB_TEXT,
)


def find_window_by_title(
    title_needles: tuple[str, ...],
    filter_false_positives: bool = False,
    timeout: float = FIND_TIMEOUT_SECONDS,
):
    """Função para achar janela de nível superior pelo título."""
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
    """Função para achar a janela principal do WeChat."""
    return find_window_by_title(TITLE_NEEDLES, filter_false_positives=True)


def _find_one(
    window,
    error_label: str,
    auto_id: str | None = None,
    timeout: float = FIND_TIMEOUT_SECONDS,
    **kwargs,
):
    """Função para achar um elemento específico dentro da janela."""
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
    """Função para colocar um texto na área de transferência."""
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()


def list_sessions(window) -> list[str]:
    """Função para listar os nomes das conversas na sidebar."""
    _switch_to_tab(window, WEIXIN_TAB_TEXT)
    session_list = _find_one(window, "Lista de conversas", auto_id="session_list")
    names = []
    for item in session_list.children(control_type="ListItem"):
        auto_id = item.element_info.automation_id
        if auto_id.startswith(SESSION_ITEM_PREFIX):
            names.append(auto_id[len(SESSION_ITEM_PREFIX):])
    return names


def list_unread_sessions(window) -> list[str]:
    """Função para listar conversas com mensagem não lida."""
    _switch_to_tab(window, WEIXIN_TAB_TEXT)
    session_list = _find_one(window, "Lista de conversas", auto_id="session_list")
    names = []
    for item in session_list.children(control_type="ListItem"):
        auto_id = item.element_info.automation_id
        if not auto_id.startswith(SESSION_ITEM_PREFIX):
            continue
        lines = item.window_text().split("\n")
        if len(lines) > 1 and UNREAD_MARKER_RE.match(lines[1]):
            names.append(auto_id[len(SESSION_ITEM_PREFIX):])
    return names


def get_current_chat_name(window) -> str | None:
    """Função para pegar o nome da conversa aberta."""
    for item in window.descendants(control_type="Text"):
        if item.element_info.automation_id.endswith(CURRENT_CHAT_LABEL_SUFFIX):
            return item.window_text()
    return None


def _random_delay(low: float = 0.3, high: float = 1.0) -> None:
    """Função para pausar um tempo aleatório entre ações."""
    time.sleep(random.uniform(low, high))


def _focus_window(window) -> None:
    """Função para focar a janela antes de clicar."""
    # click_input() faz um clique de mouse de verdade nas coordenadas de
    # tela — sem trazer a janela pra frente antes (só faz isso sozinho se
    # for um diálogo). Se o WeChat não estiver em primeiro plano (ex.: o
    # terminal rodando este script está por cima), o clique cai no que
    # estiver visível ali, não no WeChat. Refoca antes de CADA ação.
    window.set_focus()
    _random_delay()


def _switch_to_tab(main_window, tab_text: str) -> None:
    """Função para trocar de aba antes de agir, nunca assumir."""
    tab_button = _find_one(
        main_window, f"Aba '{tab_text}'", title=tab_text, control_type="Button"
    )
    _focus_window(main_window)
    tab_button.click_input()


def _click_by_text(text: str, timeout: float = FIND_TIMEOUT_SECONDS) -> None:
    """Função para clicar em elemento por texto, em qualquer janela."""
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


def _click_menu_item_by_prefix(text_prefix: str, timeout: float = FIND_TIMEOUT_SECONDS) -> None:
    """Função para clicar em item de menu por prefixo."""
    deadline = time.monotonic() + timeout
    while True:
        for window in Desktop(backend="uia").windows():
            try:
                matches = [d for d in window.descendants() if d.window_text().startswith(text_prefix)]
            except Exception:
                continue
            if matches:
                matches[0].click_input()
                return
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Item de menu começando com {text_prefix!r} não encontrado.")
        time.sleep(FIND_POLL_INTERVAL_SECONDS)


def open_add_contact_dialog(main_window):
    """Função para abrir o diálogo de adicionar contato."""
    shortcuts_button = _find_one(
        main_window, "Botão 'Shortcuts'", title="Shortcuts", control_type="Button"
    )
    _focus_window(main_window)
    shortcuts_button.click_input()
    _click_by_text(ADD_CONTACTS_MENU_TEXT)
    return find_window_by_title(ADD_CONTACTS_WINDOW_TITLE)


def _close_dialog(dialog) -> None:
    """Função para fechar uma janela de diálogo secundária."""
    close_button = _find_one(dialog, "Botão de fechar", title=CLOSE_BUTTON_TEXT, control_type="Button")
    _focus_window(dialog)
    close_button.click_input()


def add_contact_by_phone(main_window, phone: str, message: str | None = None) -> str | None:
    """Função para adicionar contato pelo telefone e mandar pedido."""
    dialog = open_add_contact_dialog(main_window)

    search_field = _find_one(dialog, "Campo de busca", control_type="Edit")
    _focus_window(dialog)
    search_field.click_input()
    _random_delay()
    # Diálogo acabou de abrir: o 1º clique só ativa a janela (o cursor
    # aparece no campo, mas o clique em si não conta como foco real pra
    # digitação) — um 2º clique de verdade é o que garante o campo pronto
    # pra receber input.
    search_field.click_input()
    # Campo ainda ficava vazio mesmo focado com Ctrl+V (clipboard) — esse
    # campo de busca especificamente não reage a paste. `phone` é só
    # dígito, então digita direto via keystrokes em vez de clipboard.
    search_field.type_keys(phone, pause=0.05)
    _random_delay()

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
            _close_dialog(dialog)
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

    if message is not None:
        message_field = _find_one(
            request_window, "Campo de mensagem do pedido", control_type="Edit"
        )
        _focus_window(request_window)
        message_field.click_input()
        message_field.type_keys("^a", pause=0.05)
        _set_clipboard_text(message)
        message_field.type_keys("^v", pause=0.05)
        _random_delay()

    ok_button = _find_one(request_window, "Botão 'OK'", title="OK", control_type="Button")
    _focus_window(request_window)
    ok_button.click_input()
    _close_dialog(dialog)
    return nickname


def _find_contact_item(main_window, contact_name: str):
    """Função para achar o item do contato na aba Contacts."""
    _switch_to_tab(main_window, CONTACTS_TAB_TEXT)

    # A busca da aba Contacts filtra a lista renderizada — a lista é um
    # Recycler (StickyHeaderRecyclerListView), então um contato fora da
    # tela pode nem existir na árvore UIA ainda sem filtrar primeiro.
    search_field = _find_one(main_window, "Campo de busca de contatos", control_type="Edit")
    _focus_window(main_window)
    search_field.click_input()
    _set_clipboard_text(contact_name)
    search_field.type_keys("^v", pause=0.05)
    _random_delay()

    matches = [
        m for m in main_window.descendants(title=contact_name, control_type="ListItem")
        if m.element_info.class_name == CONTACT_ITEM_CLASS
    ]
    return matches[0] if matches else None


def find_or_start_chat(main_window, contact_name: str) -> str | None:
    """Função para procurar e abrir conversa."""
    if contact_name in list_sessions(main_window):
        open_chat(main_window, contact_name)
        return contact_name

    item = _find_contact_item(main_window, contact_name)
    if item is None:
        return None

    _focus_window(main_window)
    item.click_input()

    messages_button = _find_one(
        main_window, "Botão 'Messages'", title=MESSAGES_BUTTON_TEXT, control_type="Button"
    )
    _focus_window(main_window)
    messages_button.click_input()

    return get_current_chat_name(main_window)


def set_contact_remark(main_window, contact_name: str, remark: str) -> None:
    """Função para definir o apelido (remark) de um contato."""
    item = _find_contact_item(main_window, contact_name)
    if item is None:
        raise RuntimeError(f"Contato {contact_name!r} não encontrado na aba Contacts.")

    _focus_window(main_window)
    item.click_input()

    remark_button = _find_one(
        main_window, "Botão de remark", class_name=REMARK_VALUE_CLASS, control_type="Button"
    )
    _focus_window(main_window)
    remark_button.click_input()

    # Confirmado ao vivo: clicar vira campo editável, pré-preenchido com o
    # valor atual. Confirmar com Enter é suposição (sem dump do estado de
    # edição) — validar ao vivo.
    remark_field = _find_one(main_window, "Campo de remark", control_type="Edit")
    _focus_window(main_window)
    remark_field.click_input()
    remark_field.type_keys("^a", pause=0.05)
    _set_clipboard_text(remark)
    remark_field.type_keys("^v", pause=0.05)
    _random_delay()
    remark_field.type_keys("{ENTER}")


def open_start_group_chat_dialog(main_window):
    """Função para abrir o diálogo de criar grupo."""
    shortcuts_button = _find_one(
        main_window, "Botão 'Shortcuts'", title="Shortcuts", control_type="Button"
    )
    _focus_window(main_window)
    shortcuts_button.click_input()
    _click_by_text(START_GROUP_CHAT_MENU_TEXT)
    return find_window_by_title(START_GROUP_CHAT_WINDOW_TITLE)


def start_group_chat(main_window, contact_names: list[str]) -> str | None:
    """Função para criar um grupo com os contatos informados."""
    dialog = open_start_group_chat_dialog(main_window)

    search_field = _find_one(dialog, "Campo de busca de contatos", control_type="Edit")

    for name in contact_names:
        _focus_window(dialog)
        search_field.click_input()
        search_field.type_keys("^a", pause=0.05)
        _set_clipboard_text(name)
        search_field.type_keys("^v", pause=0.05)
        _random_delay()

        matches = [
            m for m in dialog.descendants(title=name, control_type="CheckBox")
            if m.element_info.class_name == GROUP_CONTACT_ROW_CLASS
        ]
        if not matches:
            cancel_button = _find_one(
                dialog, "Botão 'Cancel'", title="Cancel", control_type="Button"
            )
            _focus_window(dialog)
            cancel_button.click_input()
            return None
        _focus_window(dialog)
        matches[0].click_input()

    finish_button = _find_one(dialog, "Botão 'Finish'", title="Finish", control_type="Button")
    _focus_window(dialog)
    finish_button.click_input()

    return get_current_chat_name(main_window)


def open_chat(window, chat_name: str) -> None:
    """Função para abrir uma conversa já existente na sidebar."""
    _switch_to_tab(window, WEIXIN_TAB_TEXT)
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
    """Função para enviar mensagens para novas conversas."""
    open_chat(window, chat_name)
    input_field = _find_one(window, "Campo de mensagem", auto_id="chat_input_field")
    _focus_window(window)
    input_field.click_input()
    _set_clipboard_text(text)
    input_field.type_keys("^v", pause=0.05)
    _random_delay(0.8, 1.5)  # servidor lento; dá tempo do paste refletir antes de enviar
    send_button = _find_one(window, "Botão 'Send'", title="Send", control_type="Button")
    _focus_window(window)
    send_button.click_input()


def send_file(window, chat_name: str, filepath: str) -> None:
    """Função para enviar um arquivo dentro de uma conversa."""
    open_chat(window, chat_name)
    send_file_button = _find_one(
        window, "Botão 'Send File'", title=SEND_FILE_BUTTON_TEXT, control_type="Button"
    )
    _focus_window(window)
    send_file_button.click_input()

    dialog = find_window_by_title(SELECT_FILE_WINDOW_TITLE)

    filename_field = _find_one(
        dialog, "Campo de nome de arquivo", title=FILE_NAME_FIELD_LABEL, control_type="Edit"
    )
    _focus_window(dialog)
    filename_field.click_input()
    filename_field.type_keys("^a", pause=0.05)
    _set_clipboard_text(filepath)
    filename_field.type_keys("^v", pause=0.05)
    _random_delay()

    open_button = _find_one(
        dialog, "Botão 'Open'", auto_id=DIALOG_PRIMARY_BUTTON_ID, control_type="Button"
    )
    _focus_window(dialog)
    open_button.click_input()


def download_last_document(window, chat_name: str, save_dir: str) -> str:
    """Função para baixar o último arquivo de uma conversa."""
    open_chat(window, chat_name)
    message_list = _find_one(window, "Lista de mensagens", auto_id="chat_message_list")

    file_bubbles = [
        item for item in message_list.children(control_type="ListItem")
        if item.element_info.class_name == FILE_BUBBLE_CLASS
    ]
    if not file_bubbles:
        raise RuntimeError(f"Nenhuma mensagem de arquivo encontrada em {chat_name!r}.")

    bubble = file_bubbles[-1]
    bubble_text = bubble.window_text()
    lines = bubble_text.split("\n")
    filename = lines[1] if len(lines) > 1 else None
    if not filename:
        raise RuntimeError(f"Não consegui ler o nome do arquivo na bolha: {bubble_text!r}")
    not_downloaded = NOT_DOWNLOADED_MARKER in bubble_text

    _focus_window(window)
    bubble.right_click_input()
    _click_menu_item_by_prefix(DOWNLOAD_TO_MENU_PREFIX if not_downloaded else SAVE_AS_MENU_PREFIX)

    dialog = find_window_by_title(SAVE_DIALOG_WINDOW_TITLE)

    save_path = str(Path(save_dir) / filename)
    filename_field = _find_one(
        dialog, "Campo de nome de arquivo", title=FILE_NAME_FIELD_LABEL, control_type="Edit"
    )
    _focus_window(dialog)
    filename_field.click_input()
    filename_field.type_keys("^a", pause=0.05)
    _set_clipboard_text(save_path)
    filename_field.type_keys("^v", pause=0.05)
    _random_delay()

    save_button = _find_one(
        dialog, "Botão 'Save'", auto_id=DIALOG_PRIMARY_BUTTON_ID, control_type="Button"
    )
    _focus_window(dialog)
    save_button.click_input()

    return save_path


def read_messages(window, chat_name: str | None = None) -> list[str]:
    """Função para ler as mensagens de uma conversa."""
    if chat_name:
        open_chat(window, chat_name)
    message_list = _find_one(window, "Lista de mensagens", auto_id="chat_message_list")
    texts = []
    for item in message_list.children(control_type="ListItem"):
        if item.element_info.class_name == MESSAGE_TEXT_CLASS:
            texts.append(item.window_text())
    return texts
