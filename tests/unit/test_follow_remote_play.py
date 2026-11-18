"""Following a job that another controller started on the same machine."""

import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from carveracontroller.Controller import Controller
from carveracontroller.main import Makera

TEMP_DIR = os.path.join(os.sep, "tmp", "carvera-test")


def _root(downloading=False, uploading=False):
    root = Mock()
    root.temp_dir = TEMP_DIR
    root.downloading = downloading
    root.uploading = uploading
    root.loading_file = False
    root.controller = SimpleNamespace(log=Mock())
    return root


def _follow(line, selected_remote_filename="", root=None):
    root = root or _root()
    app = SimpleNamespace(selected_remote_filename=selected_remote_filename, selected_local_filename="")
    with (
        patch("carveracontroller.main.App.get_running_app", return_value=app),
        patch("carveracontroller.main.threading.Thread") as thread,
    ):
        Makera.follow_remote_play(root, line)
    return root, app, thread


def test_job_started_elsewhere_is_selected_and_downloaded_without_popups():
    root, app, thread = _follow("Playing /sd/gcodes/job 1.nc", "/sd/gcodes/other.nc")

    local_path = os.path.join(TEMP_DIR, "gcodes/job 1.nc")
    assert app.selected_remote_filename == "/sd/gcodes/job 1.nc"
    assert app.selected_local_filename == local_path
    assert root.downloading_file == "/sd/gcodes/job 1.nc"
    assert root.downloading_config is False
    thread.assert_called_once_with(
        target=root.doDownload,
        args=("/sd/gcodes/job 1.nc", local_path, False, False),
        daemon=True,
    )
    thread.return_value.start.assert_called_once_with()


def test_own_selected_file_is_not_followed():
    _root_, app, thread = _follow("Playing /sd/gcodes/job.nc", "/sd/gcodes/job.nc")

    thread.assert_not_called()
    assert app.selected_local_filename == ""


def test_own_selected_file_with_windows_separators_is_not_followed():
    _root_, _app, thread = _follow("Playing /sd/gcodes/job.nc", "\\sd\\gcodes\\job.nc")

    thread.assert_not_called()


def test_lines_without_a_played_sd_path_are_ignored():
    for line in ("Playing file resumed", "Playing /other/job.nc", "Not Playing /sd/gcodes/job.nc"):
        _root_, _app, thread = _follow(line)
        thread.assert_not_called()


def test_job_started_elsewhere_during_a_transfer_is_reported_not_followed():
    root, app, thread = _follow("Playing /sd/gcodes/job.nc", root=_root(downloading=True))

    thread.assert_not_called()
    assert app.selected_remote_filename == ""
    root.controller.log.put.assert_called_once()
    kind, text = root.controller.log.put.call_args[0][0]
    assert kind == Controller.MSG_NORMAL
    assert "/sd/gcodes/job.nc" in text


def test_failed_background_download_writes_mdi_error_instead_of_popup(tmp_path):
    root = Mock()
    root.downloading_config = False
    root.controller.comms.uses_framed_transfer = True
    root.controller.stream.download.return_value = None
    root.controller.stream.modem.download_md5_failed = False
    local_path = str(tmp_path / "gcodes" / "job.nc")

    with (
        patch("carveracontroller.main.App.get_running_app"),
        patch("carveracontroller.main.Clock.schedule_once") as schedule_once,
    ):
        Makera.doDownload(root, "/sd/gcodes/job.nc", local_path, False, False)

    root.controller.log.put.assert_called_once_with((Controller.MSG_ERROR, "Download file error!"))
    scheduled = [call.args[0] for call in schedule_once.call_args_list]
    assert not any(getattr(cb, "func", None) is root.show_message_popup for cb in scheduled)


def test_failed_download_still_opens_popup_by_default(tmp_path):
    root = Mock()
    root.downloading_config = False
    root.controller.comms.uses_framed_transfer = True
    root.controller.stream.download.return_value = None
    root.controller.stream.modem.download_md5_failed = False
    local_path = str(tmp_path / "gcodes" / "job.nc")

    with (
        patch("carveracontroller.main.App.get_running_app"),
        patch("carveracontroller.main.Clock.schedule_once") as schedule_once,
    ):
        Makera.doDownload(root, "/sd/gcodes/job.nc", local_path, False)

    root.controller.log.put.assert_not_called()
    scheduled = [call.args[0] for call in schedule_once.call_args_list]
    assert any(getattr(cb, "func", None) is root.show_message_popup for cb in scheduled)
