#===========================================================================
#  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
#---------------------------------------------------------------------------
#  公众号 / 视频号：芯片验证日记
#  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
#
#  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
#  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
#===========================================================================

"""SHM (Cadence Xcelium / SimVision) waveform support.

Unit checks for format detection, database path normalisation and versioning,
plus end-to-end conversion through a stand-in ``simvisdbutil`` (a script that
"exports" a fixture VCD), so the SHM path is covered without Xcelium. When the
real ``simvisdbutil`` and ``xrun`` are available, an extra test dumps a real
SHM and converts it. Conversion tests need vcd2fst.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

from wave_mcp import convert, pipeline                                   # noqa: E402

FIXTURE_VCD = os.path.join(ROOT, "examples", "sample", "dump.vcd")


def _make_shm(parent, name="waves"):
    db = parent / f"{name}.shm"
    db.mkdir()
    (db / f"{name}.trn").write_bytes(b"trn-v1")
    (db / f"{name}.dsn").write_bytes(b"dsn-v1")
    return db


# ---------------------------------------------------------------------------
# detection and normalisation
# ---------------------------------------------------------------------------

class TestKind:
    def test_extensions(self):
        assert convert.waveform_kind("waves.shm") == "shm"
        assert convert.waveform_kind("/a/WAVES.SHM/") == "shm"
        assert convert.waveform_kind("waves.shm/waves.trn") == "shm"
        assert convert.waveform_kind("waves.shm/waves.dsn") == "shm"

    def test_directory_with_trn(self, tmp_path):
        d = tmp_path / "dumpdir"
        d.mkdir()
        (d / "x.trn").write_bytes(b"")
        assert convert.waveform_kind(str(d)) == "shm"

    def test_plain_directory_rejected(self, tmp_path):
        with pytest.raises(convert.UnsupportedWaveformError, match=r"\.shm"):
            convert.waveform_kind(str(tmp_path))

    def test_database_path(self, tmp_path):
        db = _make_shm(tmp_path)
        assert convert.shm_database(str(db / "waves.trn")) == str(db)
        assert convert.shm_database(str(db / "waves.dsn")) == str(db)
        assert convert.shm_database(str(db) + "/") == str(db)
        loose = tmp_path / "loose.dsn"
        assert convert.shm_database(str(loose)) == str(tmp_path / "loose.trn")

    def test_beside_path_of_directory(self, tmp_path):
        db = _make_shm(tmp_path)
        assert convert.beside_path(str(db)) == str(tmp_path / "waves.fst")


class TestVersion:
    def test_changes_with_member_content(self, tmp_path):
        db = _make_shm(tmp_path)
        v1 = convert.source_version(str(db))
        assert v1
        time.sleep(0.01)
        (db / "waves.trn").write_bytes(b"trn-v2-longer")
        assert convert.source_version(str(db)) != v1

    def test_bytes_sum_members(self, tmp_path):
        db = _make_shm(tmp_path)
        assert convert.source_bytes(str(db)) == 12


class TestHelpers:
    def test_option_lines(self, tmp_path):
        sig = tmp_path / "sigs.txt"
        sig.write_text("tb/u_dut/a\n# comment\n\n tb.b  # trailing\n")
        lines = convert._shm_option_lines(  # pylint: disable=protected-access
            ["tb/u_dut", "top.x"], str(sig))
        assert lines == ["-scope tb.u_dut all", "-scope top.x all",
                         "-signal tb.u_dut.a", "-signal tb.b"]

    def test_errors_detected_despite_rc0(self):
        out = ("Exporting VCD database file: x.vcd\n\nsimvisdbutil: "
               "*F,BDSIGNM: The signal name on the following line was not "
               "found:\n\t\"tb.nope\".\n")
        errs = convert._simvis_errors(out)  # pylint: disable=protected-access
        assert len(errs) == 1 and "tb.nope" in errs[0]
        assert not convert._simvis_errors(  # pylint: disable=protected-access
            "Translation 100% done.")


# ---------------------------------------------------------------------------
# end-to-end with a stand-in simvisdbutil
# ---------------------------------------------------------------------------

@pytest.fixture()
def fake_env(tmp_path, monkeypatch):
    if not os.path.exists(FIXTURE_VCD):
        pytest.skip("sample VCD not available")
    try:
        convert._check_bin()  # pylint: disable=protected-access
    except convert.ConversionError:
        pytest.skip("vcd2fst not available")
    monkeypatch.setenv("WAVE_MCP_CACHE_ROOT", str(tmp_path / "cache"))
    log = tmp_path / "calls.log"
    fake = tmp_path / "bin" / "simvisdbutil"
    fake.parent.mkdir()
    fake.write_text(textwrap.dedent(f"""\
        #!/bin/sh
        echo "$@" >> {log}
        out=""
        while [ $# -gt 0 ]; do
            case "$1" in -output) out="$2"; shift;; esac
            shift
        done
        [ -n "$out" ] || exit 2
        cp {FIXTURE_VCD} "$out"
        echo "Translation 100% done."
        """))
    fake.chmod(0o755)
    monkeypatch.setenv("SIMVISDBUTIL_BIN", str(fake))
    src = tmp_path / "run"
    src.mkdir()
    return {"db": _make_shm(src), "dir": src, "log": log}


class TestConversion:
    def test_resolve_writes_beside_and_reuses(self, fake_env):
        db = fake_env["db"]
        got = convert.resolve_waveform(str(db / "waves.trn"))
        assert got["kind"] == "shm"
        assert got["source"] == str(db)
        assert got["placement"] == "beside"
        assert got["fst_path"] == str(fake_env["dir"] / "waves.fst")
        # only the FST lands beside: no intermediate VCD left over
        assert sorted(os.listdir(fake_env["dir"])) == ["waves.fst", "waves.shm"]
        again = convert.resolve_waveform(str(db))
        assert again["cached"] is True
        assert len(fake_env["log"].read_text().splitlines()) == 1

    def test_rerun_simulation_reconverts(self, fake_env):
        db = fake_env["db"]
        convert.resolve_waveform(str(db))
        time.sleep(0.01)
        (db / "waves.trn").write_bytes(b"trn-after-resim")
        got = convert.resolve_waveform(str(db))
        assert got["cached"] is False
        assert "changed" in (got["notice"] or "")

    def test_partial_goes_to_cache_with_options(self, fake_env):
        got = convert.cached_fst(str(fake_env["db"]), kind="shm",
                                 scopes=["tb/u_dut"])
        assert got["placement"] == "cache"
        assert os.path.exists(got["fst_path"])
        call = fake_env["log"].read_text()
        assert "-file" in call and "-vcd" in call

    def test_prepare_session(self, fake_env, tmp_path):
        res = pipeline.prepare_session(str(tmp_path / "sess"),
                                       str(fake_env["db"]), top="",
                                       filelist=None)
        names = [s["step"] for s in res["steps"]]
        assert "convert_shm_to_fst" in names

    def test_export_failure_reported(self, fake_env, tmp_path, monkeypatch):
        bad = tmp_path / "bin" / "bad_simvisdbutil"
        bad.write_text("#!/bin/sh\necho 'simvisdbutil: *F,MKEXPF: bad scope "
                       "name \"tb.x\".'\nexit 1\n")
        bad.chmod(0o755)
        monkeypatch.setenv("SIMVISDBUTIL_BIN", str(bad))
        with pytest.raises(convert.ConversionError, match="MKEXPF"):
            convert.convert_shm(str(fake_env["db"]), str(tmp_path / "o.fst"),
                                scopes=["tb.x"])
        assert not [n for n in os.listdir(tmp_path) if n.endswith(".vcd")]

    def test_missing_binary(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SIMVISDBUTIL_BIN", str(tmp_path / "nope"))
        assert convert.resolve_simvisdbutil() is None
        db = _make_shm(tmp_path)
        with pytest.raises(convert.ConversionError, match="simvisdbutil"):
            convert.convert_shm(str(db))


# ---------------------------------------------------------------------------
# real Xcelium, when present
# ---------------------------------------------------------------------------

def test_real_xcelium_shm(tmp_path, monkeypatch):
    monkeypatch.delenv("SIMVISDBUTIL_BIN", raising=False)
    if convert.resolve_simvisdbutil() is None or not shutil.which("xrun"):
        pytest.skip("Xcelium (xrun + simvisdbutil) not available")
    try:
        convert._check_bin()  # pylint: disable=protected-access
    except convert.ConversionError:
        pytest.skip("vcd2fst not available")
    monkeypatch.setenv("WAVE_MCP_CACHE_ROOT", str(tmp_path / "cache"))
    (tmp_path / "tb.sv").write_text(textwrap.dedent("""\
        module tb;
          reg clk = 0; reg [3:0] cnt = 0;
          always #5 clk = ~clk;
          always @(posedge clk) cnt <= cnt + 1;
          initial begin
            $shm_open("waves.shm"); $shm_probe(tb, "AS");
            #200 $finish;
          end
        endmodule
        """))
    proc = subprocess.run(["xrun", "-q", "-access", "+r", "tb.sv"],
                          cwd=tmp_path, capture_output=True, text=True,
                          timeout=600)
    if proc.returncode != 0 or not (tmp_path / "waves.shm").is_dir():
        pytest.skip(f"xrun could not run here: {proc.stdout[-300:]}")
    got = convert.resolve_waveform(str(tmp_path / "waves.shm"))
    assert got["fst_path"] == str(tmp_path / "waves.fst")
    from pylibfst import ffi, lib
    ctx = lib.fstReaderOpen(got["fst_path"].encode())
    assert ctx != ffi.NULL
    lib.fstReaderClose(ctx)
