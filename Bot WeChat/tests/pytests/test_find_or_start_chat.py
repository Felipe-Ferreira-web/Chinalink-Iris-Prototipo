"""Caracterização de find_or_start_chat: sessão existente usa
open_chat; sem sessão busca em Contacts; sem match retorna None.
pywinauto mockado — verificação real é manual (ver docs/README.md)."""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from wechat import wechat


def _find_one_by_label(mapping):
    def _side_effect(window, error_label, *args, **kwargs):
        return mapping[error_label]
    return _side_effect


def _patch_wechat_internals(stack):
    # Patch em wechat.wechat (não wechat.X): é o módulo onde as funções
    # foram definidas, e é lá que o nome é resolvido em tempo de chamada.
    return {
        "list_sessions": stack.enter_context(patch("wechat.wechat.list_sessions")),
        "open_chat": stack.enter_context(patch("wechat.wechat.open_chat")),
        "get_current_chat_name": stack.enter_context(patch("wechat.wechat.get_current_chat_name")),
        "set_clipboard_text": stack.enter_context(patch("wechat.wechat._set_clipboard_text")),
        "random_delay": stack.enter_context(patch("wechat.wechat._random_delay")),
        "focus_window": stack.enter_context(patch("wechat.wechat._focus_window")),
        "find_one": stack.enter_context(patch("wechat.wechat._find_one")),
    }


def test_already_in_sidebar_uses_fast_path():
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)
        main_window = MagicMock()

        mocks["list_sessions"].return_value = ["Felipe", "Outra Pessoa"]

        result = wechat.find_or_start_chat(main_window, "Felipe")

        assert result == "Felipe"
        mocks["open_chat"].assert_called_once_with(main_window, "Felipe")
        mocks["find_one"].assert_not_called()


def test_found_via_contacts_tab():
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)
        main_window = MagicMock()

        tab_button = MagicMock()
        search_field = MagicMock()
        messages_button = MagicMock()
        contact_item = MagicMock()
        contact_item.element_info.class_name = wechat.CONTACT_ITEM_CLASS

        mocks["list_sessions"].return_value = []
        mocks["find_one"].side_effect = _find_one_by_label({
            "Aba 'Contacts'": tab_button,
            "Campo de busca de contatos": search_field,
            "Botão 'Messages'": messages_button,
        })
        main_window.descendants.side_effect = lambda **kwargs: (
            [contact_item] if kwargs.get("title") == "Felipe" else []
        )
        mocks["get_current_chat_name"].return_value = "Felipe"

        result = wechat.find_or_start_chat(main_window, "Felipe")

        assert result == "Felipe"
        tab_button.click_input.assert_called_once()
        search_field.type_keys.assert_any_call("^v", pause=0.05)
        mocks["set_clipboard_text"].assert_any_call("Felipe")
        contact_item.click_input.assert_called_once()
        messages_button.click_input.assert_called_once()


def test_not_found_returns_none():
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)
        main_window = MagicMock()

        tab_button = MagicMock()
        search_field = MagicMock()

        mocks["list_sessions"].return_value = []
        mocks["find_one"].side_effect = _find_one_by_label({
            "Aba 'Contacts'": tab_button,
            "Campo de busca de contatos": search_field,
        })
        main_window.descendants.side_effect = lambda **kwargs: []

        result = wechat.find_or_start_chat(main_window, "Ninguém")

        assert result is None
        mocks["get_current_chat_name"].assert_not_called()
