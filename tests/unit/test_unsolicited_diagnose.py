"""Diagnose ({...}) reports that arrive without this controller's own `diagnose` request."""

from unittest.mock import Mock, patch

from kivy.config import Config

from carveracontroller.CNC import CNC
from carveracontroller.Controller import Controller
from carveracontroller.main import Makera


def _controller():
    ctrl = Controller(CNC(), lambda _line: None, False)
    # streamIO() initialises these before any line is parsed.
    ctrl.sio_status = False
    ctrl.sio_diagnose = False
    ctrl.diagnoseUpdate = False
    return ctrl


def _drain_log(ctrl):
    lines = []
    while not ctrl.log.empty():
        lines.append(ctrl.log.get_nowait()[1])
    return lines


def test_unsolicited_diagnose_is_logged_and_ignored_by_default():
    ctrl = _controller()
    CNC.vars["sw_light"] = 0

    ctrl.parseLine("{S:0,5000|G:1|RSSI:-57}")

    assert CNC.vars["sw_light"] == 0
    assert ctrl.diagnoseUpdate is False
    assert _drain_log(ctrl) == ["{S:0,5000|G:1|RSSI:-57}"]


def test_unsolicited_diagnose_is_applied_when_enabled():
    ctrl = _controller()
    ctrl.accept_unsolicited_diagnose = True
    CNC.vars["sw_light"] = 0

    ctrl.parseLine("{S:0,5000|G:1|RSSI:-57}")

    assert CNC.vars["sw_light"] == 1
    assert ctrl.diagnoseUpdate is True
    assert _drain_log(ctrl) == []


def test_requested_diagnose_still_clears_pending_request_when_enabled():
    ctrl = _controller()
    ctrl.accept_unsolicited_diagnose = True
    ctrl.sio_diagnose = True
    CNC.vars["sw_light"] = 1

    ctrl.parseLine("{S:0,5000|G:0}")

    assert CNC.vars["sw_light"] == 0
    assert ctrl.sio_diagnose is False


def test_non_diagnose_brace_text_stays_in_mdi_when_enabled():
    ctrl = _controller()
    ctrl.accept_unsolicited_diagnose = True

    ctrl.parseLine("{hello}")

    assert ctrl.diagnoseUpdate is False
    assert _drain_log(ctrl) == ["{hello}"]


def test_applying_the_setting_updates_the_running_controller():
    if not Config.has_section("carvera"):
        Config.add_section("carvera")
    Config.set("carvera", "accept_unsolicited_diagnose", "1")
    root = Mock()
    root.controller_setting_change_list = {"accept_unsolicited_diagnose": "1"}
    root.controller = _controller()

    try:
        with patch("carveracontroller.main.App.get_running_app"):
            Makera.apply_controller_setting_changes(root)
    finally:
        Config.remove_option("carvera", "accept_unsolicited_diagnose")

    assert root.controller.accept_unsolicited_diagnose is True
