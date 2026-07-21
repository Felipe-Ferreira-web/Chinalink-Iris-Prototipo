"""Caracterização de set_contact_remark — trava o comportamento
confirmado ao vivo (2026-07-21): acha o contato na aba Contacts, abre o
campo de remark (clique vira Edit pré-preenchido), cola o novo valor e
confirma com Enter. pywinauto é todo mockado; a verificação real é
manual, no servidor, contra o WeChat de verdade (ver docs/README.md).
"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from wechat import wechat


def _find_one_by_label(mapping):
    def _side_effect(window, error_label, *args, **kwargs):
        return mapping[error_label]
    return _side_effect


def _patch_wechat_internals(stack):
    # Patch em wechat.wechat (não wechat.X): é o módulo onde as funções
    # foram definidas, e é lá que o nome é resolvido em tempo de chamada.
    return {
        "set_clipboard_text": stack.enter_context(patch("wechat.wechat._set_clipboard_text")),
        "random_delay": stack.enter_context(patch("wechat.wechat._random_delay")),
        "focus_window": stack.enter_context(patch("wechat.wechat._focus_window")),
        "find_one": stack.enter_context(patch("wechat.wechat._find_one")),
    }


def test_sets_remark_successfully():
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)
        main_window = MagicMock()

        tab_button = MagicMock()
        search_field = MagicMock()
        remark_button = MagicMock()
        remark_field = MagicMock()
        contact_item = MagicMock()
        contact_item.element_info.class_name = wechat.CONTACT_ITEM_CLASS

        mocks["find_one"].side_effect = _find_one_by_label({
            "Aba 'Contacts'": tab_button,
            "Campo de busca de contatos": search_field,
            "Botão de remark": remark_button,
            "Campo de remark": remark_field,
        })
        main_window.descendants.side_effect = lambda **kwargs: (
            [contact_item] if kwargs.get("title") == "Felipe" else []
        )

        wechat.set_contact_remark(main_window, "Felipe", "Apelido Teste")

        tab_button.click_input.assert_called_once()
        contact_item.click_input.assert_called_once()
        remark_button.click_input.assert_called_once()
        remark_field.type_keys.assert_any_call("^a", pause=0.05)
        remark_field.type_keys.assert_any_call("^v", pause=0.05)
        remark_field.type_keys.assert_any_call("{ENTER}")
        mocks["set_clipboard_text"].assert_any_call("Apelido Teste")


def test_contact_not_found_raises():
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)
        main_window = MagicMock()

        tab_button = MagicMock()
        search_field = MagicMock()

        mocks["find_one"].side_effect = _find_one_by_label({
            "Aba 'Contacts'": tab_button,
            "Campo de busca de contatos": search_field,
        })
        main_window.descendants.side_effect = lambda **kwargs: []

        with pytest.raises(RuntimeError):
            wechat.set_contact_remark(main_window, "Ninguém", "X")
