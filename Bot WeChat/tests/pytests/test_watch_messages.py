"""Caracterização de watch_messages.main: usa [N] da sidebar (não estado
local) pra saber quantas mensagens são novas, reconsulta pendentes a cada
passo, e encerra assim que não sobrar pendente ou ao bater timeout/teto de
mensagens. pywinauto mockado — verificação real é manual (ver
docs/README.md)."""

import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

MANUAL_TESTS_DIR = str(Path(__file__).resolve().parent.parent / "manual")
if MANUAL_TESTS_DIR not in sys.path:
    sys.path.insert(0, MANUAL_TESTS_DIR)

import watch_messages  # noqa: E402


def _patch_watch_messages_internals(stack):
    return {
        "connect": stack.enter_context(patch("watch_messages.connect")),
        "list_unread_sessions": stack.enter_context(
            patch("wechat.wechat.list_unread_sessions")
        ),
        "read_messages": stack.enter_context(patch("wechat.wechat.read_messages")),
        "monotonic": stack.enter_context(patch("watch_messages.time.monotonic")),
        "sleep": stack.enter_context(patch("watch_messages.time.sleep")),
    }


def test_no_pending_exits_immediately_without_sleep():
    with ExitStack() as stack:
        mocks = _patch_watch_messages_internals(stack)
        mocks["connect"].return_value = (MagicMock(), MagicMock())
        mocks["monotonic"].return_value = 0.0
        mocks["list_unread_sessions"].return_value = []

        watch_messages.main()

        mocks["read_messages"].assert_not_called()
        mocks["sleep"].assert_not_called()


def test_uses_unread_marker_count_not_full_history():
    with ExitStack() as stack:
        mocks = _patch_watch_messages_internals(stack)
        mocks["connect"].return_value = (MagicMock(), MagicMock())
        mocks["monotonic"].return_value = 0.0
        mocks["list_unread_sessions"].side_effect = [
            [("Felipe", 1)],
            [],
        ]
        mocks["read_messages"].return_value = ["mensagem antiga", "Fala"]

        watch_messages.main()

        # unread_count=1 -> só a última mensagem é nova, resto é histórico.
        mocks["read_messages"].assert_called_once_with(mocks["connect"].return_value[0], "Felipe")


def test_processes_multiple_pending_sessions_in_sidebar_order():
    with ExitStack() as stack:
        mocks = _patch_watch_messages_internals(stack)
        mocks["connect"].return_value = (MagicMock(), MagicMock())
        mocks["monotonic"].return_value = 0.0
        mocks["list_unread_sessions"].side_effect = [
            [("Felipe", 1), ("Victor Silva", 1)],
            [("Victor Silva", 1)],
            [],
        ]
        mocks["read_messages"].side_effect = [
            ["Fala"],
            ["ok adicionado"],
        ]

        with patch("watch_messages.log") as mock_log:
            watch_messages.main()

        assert mocks["read_messages"].call_count == 2
        info_calls = [call.args for call in mock_log.info.call_args_list]
        assert ("[%d] %s: %r", 1, "Felipe", "Fala") in info_calls
        assert ("[%d] %s: %r", 2, "Victor Silva", "ok adicionado") in info_calls


def test_stops_at_message_cap_even_with_more_pending():
    with ExitStack() as stack:
        mocks = _patch_watch_messages_internals(stack)
        mocks["connect"].return_value = (MagicMock(), MagicMock())
        mocks["monotonic"].return_value = 0.0
        mocks["list_unread_sessions"].return_value = [("Grupo Ativo", 999)]
        mocks["read_messages"].return_value = [f"msg {i}" for i in range(999)]

        with patch("watch_messages.log") as mock_log:
            watch_messages.main()

        warning_calls = [call.args[0] for call in mock_log.warning.call_args_list]
        assert any("Limite de" in msg for msg in warning_calls)
        info_calls = [call.args for call in mock_log.info.call_args_list]
        notification_logs = [c for c in info_calls if c[0] == "[%d] %s: %r"]
        assert len(notification_logs) == watch_messages.MAX_MESSAGES_PER_RUN


def test_stops_at_timeout_even_with_pending_left():
    with ExitStack() as stack:
        mocks = _patch_watch_messages_internals(stack)
        mocks["connect"].return_value = (MagicMock(), MagicMock())
        # 1ª checagem do while: dentro do prazo. 2ª: já estourou.
        mocks["monotonic"].side_effect = [0.0, 0.0, 999.0]
        mocks["list_unread_sessions"].return_value = [("Felipe", 1)]
        mocks["read_messages"].return_value = ["Fala"]

        watch_messages.main()

        assert mocks["read_messages"].call_count == 1
