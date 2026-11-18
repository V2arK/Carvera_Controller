"""Main-screen Light button following switch state shared by a multi-client gateway."""

from types import SimpleNamespace
from unittest.mock import Mock

from carveracontroller.main import Makera


def _root(is_accepting_shared_state):
    root = SimpleNamespace(
        controller=SimpleNamespace(accept_unsolicited_diagnose=is_accepting_shared_state),
        light_state=True,
        bind_light_toggle_to_property=Mock(),
        _on_light_state_changed=Mock(),
    )
    return root


def test_light_button_is_bound_and_synced_on_connect_when_accepting_shared_state():
    root = _root(is_accepting_shared_state=True)

    Makera.bind_light_toggle_for_shared_state(root)

    root.bind_light_toggle_to_property.assert_called_once_with()
    root._on_light_state_changed.assert_called_once_with(root, True)
    assert root._light_toggle_bound is True


def test_light_button_is_bound_only_once_per_connection():
    root = _root(is_accepting_shared_state=True)
    root._light_toggle_bound = True

    Makera.bind_light_toggle_for_shared_state(root)

    root.bind_light_toggle_to_property.assert_not_called()
    root._on_light_state_changed.assert_not_called()


def test_light_button_binding_is_left_to_config_load_when_setting_is_off():
    root = _root(is_accepting_shared_state=False)

    Makera.bind_light_toggle_for_shared_state(root)

    root.bind_light_toggle_to_property.assert_not_called()
    assert not hasattr(root, "_light_toggle_bound")
