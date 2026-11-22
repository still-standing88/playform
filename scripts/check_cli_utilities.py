"""CLI discovery, installation and preferences regressions, with isolated app data.

Run with the project's Python: python scripts/check_cli_utilities.py
"""
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utilities import functions

_test_data = tempfile.TemporaryDirectory(prefix="playform-cli-tests-")
functions.get_app_path = lambda: _test_data.name

from utilities.i18n import install_translation

install_translation()

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from app_config import prefs
from app_constance import prefs_dict
from utilities import cli_binaries as cli
from util_download_center import install_manager
from util_download_center.download_dialog import UtilityDownloadDialog
from util_download_center.tool_fetcher import ToolFetcher
from util_download_center.tool_registry import MEDIACAP
from gui.prefs_panels.advanced_panel import AdvancedPanel
from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.mediacap import find_mediacap
from media_core.ytdlp_download.engine import _deno_args
from player.util.url import _get_deno_arg


class CliUtilitiesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=_test_data.name)
        self.root = Path(self.directory.name)
        self.original_prefs = prefs.prefs.copy()
        prefs.prefs.update({"deno_path": "", "mediacap_path": "",
                            "deno_binary": "", "mediacap_binary": ""})
        cli._CHECK_CACHE.clear()
        self.patches = [
            patch.object(cli, "get_parent_dir", return_value=str(self.root)),
            patch.object(cli.shutil, "which", return_value=None),
            patch.object(cli.subprocess, "run", side_effect=self.run_stub),
        ]
        for mock in self.patches:
            mock.start()

    def tearDown(self):
        for mock in reversed(self.patches):
            mock.stop()
        prefs.prefs.clear()
        prefs.prefs.update(self.original_prefs)
        self.directory.cleanup()

    @staticmethod
    def run_stub(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, Path(args[0]).read_text(), "")

    def binary(self, relative, output="MediaCap 1.0.0\n"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output)
        path.chmod(0o755)
        return str(path)

    def test_mediacap_prefers_valid_global_over_configured_and_bundled(self):
        global_path = self.binary("global/MediaCap.exe")
        configured = self.binary("custom/MediaCap.exe")
        self.binary("bin/MediaCap.exe")
        with patch.object(cli.sys, "platform", "win32"), patch.object(
            cli.shutil, "which", side_effect=lambda name: global_path if name == "MediaCap.exe" else None,
        ):
            self.assertEqual(cli.resolve_mediacap_binary_path({"mediacap_path": configured}), global_path)

    def test_invalid_global_falls_back_to_configured_release_filename(self):
        global_path = self.binary("global/MediaCap", "Other CLI 1.0\n")
        configured = self.binary("custom/MediaCap-cli-linux-x64")
        with patch.object(cli.sys, "platform", "linux"), patch.object(
            cli.shutil, "which", side_effect=lambda name: global_path if name == "MediaCap" else None,
        ):
            self.assertEqual(cli.resolve_mediacap_binary_path({"mediacap_path": str(Path(configured).parent)}), configured)

    def test_missing_configured_path_ignores_stale_binary_and_uses_bundle(self):
        stale = self.binary("old/MediaCap.exe")
        bundled = self.binary("bin/MediaCap.exe")
        with patch.object(cli.sys, "platform", "win32"):
            self.assertEqual(cli.resolve_mediacap_binary_path({
                "mediacap_path": str(self.root / "missing"), "mediacap_binary": stale,
            }), bundled)

    def test_missing_tools_report_preferences_and_download_location(self):
        for check in (cli.check_deno, cli.check_mediacap):
            result = check({})
            self.assertFalse(result.ok)
            self.assertFalse(result.exists)
            self.assertIn("Preferences", result.message)
            self.assertIn("Get/Update Utilities", result.message)
        missing = str(self.root / "configured" / "MediaCap.exe")
        result = cli.check_mediacap({"mediacap_path": missing})
        self.assertEqual(result.path, missing)

    def test_invalid_cli_and_failed_or_timed_out_process_are_rejected(self):
        path = self.binary("wrong.exe", "Unrelated program 1.0\n")
        self.assertFalse(cli.check_cli_binary("mediacap", path).ok)
        with patch.object(cli.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "MediaCap 1.0.0", "bad architecture")):
            result = cli.check_cli_binary("mediacap", path)
            self.assertFalse(result.ok)
            self.assertIn("bad architecture", result.message)
        with patch.object(cli.subprocess, "run", side_effect=subprocess.TimeoutExpired([path], 5)):
            self.assertFalse(cli.check_cli_binary("mediacap", path).ok)

    def test_linux_nonexecutable_file_is_rejected_without_launching(self):
        path = self.binary("MediaCap")
        with patch.object(cli.sys, "platform", "linux"), patch.object(cli.os, "access", return_value=False), patch.object(cli.subprocess, "run") as run:
            result = cli.check_cli_binary("mediacap", path)
            self.assertFalse(result.ok)
            run.assert_not_called()

    def test_version_probe_is_cached_and_invalidated_when_binary_changes(self):
        path = self.binary("MediaCap.exe")
        with patch.object(cli.subprocess, "run", side_effect=self.run_stub) as run:
            self.assertTrue(cli.check_cli_binary("mediacap", path).ok)
            self.assertTrue(cli.check_cli_binary("mediacap", path).ok)
            self.assertEqual(run.call_count, 1)
            Path(path).write_text("Not MediaCap any more\n")
            self.assertFalse(cli.check_cli_binary("mediacap", path).ok)
            self.assertEqual(run.call_count, 2)

    def test_deno_path_is_used_by_player_and_downloader(self):
        path = self.binary("custom/deno.exe", "deno 2.8.3\nv8 14.8\n")
        prefs.prefs["deno_path"] = str(Path(path).parent)
        with patch.object(cli.sys, "platform", "win32"):
            expected = ["--js-runtimes", f"deno:{path}", "--remote-components", "ejs:github"]
            self.assertEqual(_get_deno_arg(), expected)
            self.assertEqual(_deno_args(), expected)
        prefs.prefs["deno_path"] = ""
        self.assertEqual(_deno_args(), ["--remote-components", "ejs:github"])

    def test_capture_resolution_updates_after_install_and_preference_edit(self):
        capabilities = CaptureCapabilities()
        with patch.object(cli.sys, "platform", "win32"):
            self.assertIsNone(capabilities.executable)
            bundled = self.binary("bin/MediaCap.exe")
            self.assertEqual(capabilities.executable, bundled)
            custom = self.binary("custom/MediaCap.exe")
            prefs.prefs["mediacap_path"] = custom
            self.assertEqual(capabilities.executable, custom)
            self.assertEqual(find_mediacap(), custom)

    def test_mediacap_release_assets_are_exact_for_each_supported_platform(self):
        fetcher = ToolFetcher()
        for platform_name, arch, expected in (
            ("windows", "x86_64", "MediaCap-cli-windows-x64.exe"),
            ("windows", "aarch64", "MediaCap-cli-windows-arm64.exe"),
            ("linux", "x86_64", "MediaCap-cli-linux-x64"),
            ("linux", "aarch64", "MediaCap-cli-linux-arm64"),
        ):
            with self.subTest(platform=platform_name, arch=arch):
                fetcher._platform, fetcher._arch = platform_name, arch
                asset = {"name": expected, "browser_download_url": f"https://github.com/still-standing88/media-cap/releases/download/v1.0.0/{expected}"}
                selected, error = fetcher._match_asset(MEDIACAP, [{"name": expected + "-notices.txt"}, asset], {})
                self.assertEqual(selected, asset)
                self.assertEqual(error, "")
                self.assertFalse(MEDIACAP.is_zip)
                self.assertIsNone(fetcher._match_asset(MEDIACAP, [{"name": expected + "-notices.txt"}], {})[0])
        for platform_name, arch in (("macos", "x86_64"), ("linux", "riscv64")):
            fetcher._platform, fetcher._arch = platform_name, arch
            self.assertIsNone(fetcher._match_asset(MEDIACAP, [], {})[0])

    def test_installer_validates_direct_mediacap_and_sets_linux_permissions(self):
        downloaded = self.binary("downloads/MediaCap-cli-linux-x64")
        bin_dir = self.root / "installed"
        with patch.object(install_manager, "_get_bin_dir", return_value=bin_dir), patch.object(install_manager.sys, "platform", "linux"), patch.object(prefs, "save"), patch.object(install_manager.os, "chmod", wraps=os.chmod) as chmod:
            ok, message = install_manager.install_tool(downloaded, "mediacap", False, "MediaCap.exe", "MediaCap")
            self.assertTrue(ok, message)
            self.assertEqual(Path(message).name, "MediaCap")
            self.assertEqual(prefs.prefs["mediacap_path"], str(bin_dir))
            self.assertEqual(prefs.prefs["mediacap_binary"], message)
            self.assertEqual(chmod.call_args.args[1], 0o755)
            if os.name != "nt":
                self.assertTrue(os.stat(message).st_mode & 0o111)

    def test_invalid_download_preserves_existing_binary_and_preferences(self):
        existing = self.binary("bin/MediaCap.exe")
        downloaded = self.binary("downloads/MediaCap-cli-windows-x64.exe", "HTML download error\n")
        prefs.prefs["mediacap_binary"] = "original preference"
        with patch.object(install_manager, "_get_bin_dir", return_value=self.root / "bin"), patch.object(install_manager.sys, "platform", "win32"), patch.object(prefs, "save") as save:
            ok, _ = install_manager.install_tool(downloaded, "mediacap", False, "MediaCap.exe", "MediaCap")
            self.assertFalse(ok)
            self.assertEqual(Path(existing).read_text(), "MediaCap 1.0.0\n")
            self.assertEqual(prefs.prefs["mediacap_binary"], "original preference")
            save.assert_not_called()
            self.assertEqual(list((self.root / "bin").iterdir()), [Path(existing)])

    def test_deno_zip_install_records_its_path(self):
        archive = self.root / "deno.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("deno.exe", "deno 2.8.3\n")
        with patch.object(install_manager, "_get_bin_dir", return_value=self.root / "bin"), patch.object(install_manager.sys, "platform", "win32"), patch.object(prefs, "save"):
            ok, message = install_manager.install_tool(str(archive), "deno", True, "deno.exe", "deno")
            self.assertTrue(ok, message)
            self.assertEqual(prefs.prefs["deno_binary"], message)
            self.assertEqual(prefs.prefs["deno_path"], str(self.root / "bin"))

    def test_preferences_load_save_and_check_pending_path_without_saving(self):
        panel = AdvancedPanel()
        panel.load_settings(prefs.prefs)
        path = self.binary("custom/MediaCap.exe")
        for index in range(panel.path_list.count()):
            if panel.path_list.item(index).data(Qt.ItemDataRole.UserRole) == "mediacap_path":
                panel.path_list.setCurrentRow(index)
        panel._path_values["mediacap_path"] = path
        with patch.object(cli.sys, "platform", "win32"), patch("player.util.utilities.show_binary_check_result") as show:
            panel.check_selected_path()
            self.assertTrue(show.call_args.args[1].ok)
            self.assertEqual(show.call_args.args[1].path, path)
            self.assertEqual(prefs.prefs["mediacap_path"], "")
        values = prefs.prefs.copy()
        values["mediacap_binary"] = "stale"
        panel.save_settings(values)
        self.assertEqual(values["mediacap_path"], path)
        self.assertEqual(values["mediacap_binary"], "")
        for key in ("deno_path", "mediacap_path"):
            self.assertIn(key, prefs_dict.DIALOG_PREFS_KEYS)
            self.assertIn(key, prefs._dialog_subset(values))
        panel.close()

    def test_download_utilities_dialog_lists_mediacap(self):
        dialog = UtilityDownloadDialog()
        self.assertIn("MediaCap", [dialog._list.item(i).text() for i in range(dialog._list.count())])
        dialog.close()


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        from app_db import user_db, media_db
        user_db.close_connection()
        media_db.close_connection()
        _test_data.cleanup()
