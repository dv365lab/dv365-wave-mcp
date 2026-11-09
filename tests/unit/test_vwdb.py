#===========================================================================
#  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
#---------------------------------------------------------------------------
#  公众号 / 视频号：芯片验证日记
#  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
#
#  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
#  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
#===========================================================================

"""VWDB (Cadence Verisium waveform database) support.

Format detection, database path normalisation (a path inside the database, a
VWDB-only ``.shm``), FST placement for a VWDB nested in a ``.shm``, and
end-to-end conversion through a stand-in ``vwdb2vcd`` that "exports" a fixture
VCD and writes a log like the real tool. When Xcelium is installed, an extra
test dumps a real VWDB (SHM->VWDB dumping) and converts it. Conversion tests
need vcd2fst.
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


def _make_vwdb(path):
    path.mkdir(parents=True)
    (path / "vwdb_info.json").write_text('{"DSN only": false}')
    (path / "dsn_0").mkdir()
    (path / "dsn_0" / "d0").write_bytes(b"dsn")
    (path / "trn_0_0").mkdir()
    (path / "trn_0_0" / "t0").write_bytes(b"trn-v1")
    (path / ".temp").mkdir()
    return path


# ---------------------------------------------------------------------------
# detection and normalisation
# ---------------------------------------------------------------------------

class TestKind:
    def test_extension(self):
        assert convert.waveform_kind("run/waves.vwdb") == "vwdb"
        assert convert.waveform_kind("run/WAVES.VWDB/") == "vwdb"

    def test_paths_inside(self, tmp_path):
        db = _make_vwdb(tmp_path / "x.vwdb")
        assert convert.waveform_kind(str(db / "vwdb_info.json")) == "vwdb"
        assert convert.waveform_kind(str(db / "trn_0_0")) == "vwdb"
        assert convert.vwdb_database(str(db / "trn_0_0" / "t0")) == str(db)

    def test_unnamed_root(self, tmp_path):
        db = _make_vwdb(tmp_path / "ida")
        assert convert.waveform_kind(str(db)) == "vwdb"
        assert convert.vwdb_database(str(db / "dsn_0")) == str(db)

    def test_vwdb_only_shm(self, tmp_path):
        shm = tmp_path / "waves.shm"
        db = _make_vwdb(shm / "waves_ida.vwdb")
        assert convert.waveform_kind(str(shm)) == "vwdb"
        assert convert.vwdb_database(str(shm)) == str(db)

    def test_hybrid_shm_stays_shm(self, tmp_path):
        shm = tmp_path / "waves.shm"
        _make_vwdb(shm / "waves_ida.vwdb")
        (shm / "waves.trn").write_bytes(b"")
        (shm / "waves.dsn").write_bytes(b"")
        assert convert.waveform_kind(str(shm)) == "shm"
        assert convert.waveform_kind(str(shm / "waves_ida.vwdb")) == "vwdb"

    def test_ambiguous_shm(self, tmp_path):
        shm = tmp_path / "waves.shm"
        _make_vwdb(shm / "a.vwdb")
        _make_vwdb(shm / "b.vwdb")
        with pytest.raises(convert.UnsupportedWaveformError, match="several"):
            convert.vwdb_database(str(shm))

    def test_beside_path(self, tmp_path):
        assert convert.beside_path(str(tmp_path / "x.vwdb")) == \
            str(tmp_path / "x.fst")
        # nested in a .shm: beside the .shm directory, never inside it
        nested = tmp_path / "waves.shm" / "waves_ida.vwdb"
        assert convert.beside_path(str(nested)) == \
            str(tmp_path / "waves_ida.fst")


class TestVersion:
    def test_tracks_nested_files_not_scratch(self, tmp_path):
        db = _make_vwdb(tmp_path / "x.vwdb")
        v1 = convert.source_version(str(db))
        (db / ".temp" / "scratch").write_bytes(b"noise")
        assert convert.source_version(str(db)) == v1
        time.sleep(0.01)
        (db / "trn_0_0" / "t0").write_bytes(b"trn-v2-longer")
        assert convert.source_version(str(db)) != v1

    def test_shm_ignores_foreign_files(self, tmp_path):
        shm = tmp_path / "w.shm"
        shm.mkdir()
        (shm / "w.trn").write_bytes(b"t")
        (shm / "w.dsn").write_bytes(b"d")
        v1 = convert.source_version(str(shm))
        (shm / "notes.txt").write_text("x")
        assert convert.source_version(str(shm)) == v1


class TestHelpers:
    def test_log_problems(self):
        log = ("[18] [INFO][CVT] Handle value change, num of signal = 1\n"
               "[26] [INFO][CVT] Signal \"tb.nope\" not found in database\n"
               "[11] [ERROR][CVT] Dump path: ./x.dmp\n")
        probs = convert._vwdb_log_problems(log)  # pylint: disable=protected-access
        assert len(probs) == 2 and "tb.nope" in probs[0]

    def test_names(self, tmp_path):
        sig = tmp_path / "s.txt"
        sig.write_text("tb/u/a  # c\n\ntb.b\n")
        scopes, sigs = convert._vwdb_names(  # pylint: disable=protected-access
            ["/tb/u_dut/"], str(sig))
        assert scopes == ["tb.u_dut"] and sigs == ["tb.u.a", "tb.b"]


# ---------------------------------------------------------------------------
# end-to-end with a stand-in vwdb2vcd
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
    calls = tmp_path / "calls.log"
    fake = tmp_path / "bin" / "vwdb2vcd"
    fake.parent.mkdir()
    # Like the real tool: writes vwdb2vcd.log into its cwd, reports an
    # unknown signal only in that log and still exits 0.
    fake.write_text(textwrap.dedent(f"""\
        #!/bin/sh
        echo "$PWD :: $@" >> {calls}
        out=""; list=""
        while [ $# -gt 0 ]; do
            case "$1" in
                -o) out="$2"; shift;;
                -signalListFile) list="$2"; shift;;
            esac
            shift
        done
        echo "[1] [INFO][CVT] start" > vwdb2vcd.log
        if [ -n "$list" ] && grep -q nope "$list"; then
            echo '[9] [INFO][CVT] Signal "tb.nope" not found in database' \\
                >> vwdb2vcd.log
        fi
        cp {FIXTURE_VCD} "$out"
        """))
    fake.chmod(0o755)
    monkeypatch.setenv("VWDB2VCD_BIN", str(fake))
    run = tmp_path / "run"
    db = _make_vwdb(run / "waves.shm" / "waves_ida.vwdb")
    return {"db": db, "run": run, "calls": calls, "tmp": tmp_path}


class TestConversion:
    def test_resolve_writes_beside_shm_dir(self, fake_env):
        db = fake_env["db"]
        got = convert.resolve_waveform(str(db / "vwdb_info.json"))
        assert got["kind"] == "vwdb"
        assert got["source"] == str(db)
        assert got["fst_path"] == str(fake_env["run"] / "waves_ida.fst")
        assert got["placement"] == "beside"
        # nothing left behind: no VCD, no scratch dir, no vwdb2vcd.log
        assert sorted(os.listdir(fake_env["run"])) == \
            ["waves.shm", "waves_ida.fst"]
        assert sorted(os.listdir(db.parent)) == ["waves_ida.vwdb"]
        # vwdb2vcd ran in a private scratch dir, not the caller's cwd
        cwd = fake_env["calls"].read_text().split(" :: ")[0]
        assert ".vwdb-export" in cwd
        assert convert.resolve_waveform(str(db))["cached"] is True

    def test_vwdb_only_shm_entry(self, fake_env):
        got = convert.resolve_waveform(str(fake_env["db"].parent))
        assert got["kind"] == "vwdb" and got["source"] == str(fake_env["db"])

    def test_rerun_reconverts(self, fake_env):
        db = fake_env["db"]
        convert.resolve_waveform(str(db))
        time.sleep(0.01)
        (db / "trn_0_0" / "t0").write_bytes(b"after-resim")
        got = convert.resolve_waveform(str(db))
        assert got["cached"] is False

    def test_signal_not_found_is_an_error(self, fake_env):
        bad = fake_env["tmp"] / "sigs.txt"
        bad.write_text("tb.ok\ntb.nope\n")
        with pytest.raises(convert.ConversionError, match="tb.nope"):
            convert.convert_vwdb(str(fake_env["db"]),
                                 str(fake_env["tmp"] / "o.fst"),
                                 signals_file=str(bad))

    def test_scopes_partial_to_cache(self, fake_env):
        got = convert.cached_fst(str(fake_env["db"]), kind="vwdb",
                                 scopes=["tb/u_dut"])
        assert got["placement"] == "cache"
        assert "-scope tb.u_dut" in fake_env["calls"].read_text()

    def test_prepare_session(self, fake_env):
        res = pipeline.prepare_session(str(fake_env["tmp"] / "sess"),
                                       str(fake_env["db"]), top="",
                                       filelist=None)
        assert "convert_vwdb_to_fst" in [s["step"] for s in res["steps"]]

    def test_missing_binary(self, monkeypatch, tmp_path):
        monkeypatch.setenv("VWDB2VCD_BIN", str(tmp_path / "nope"))
        assert convert.resolve_vwdb2vcd() is None
        db = _make_vwdb(tmp_path / "x.vwdb")
        with pytest.raises(convert.ConversionError, match="vwdb2vcd"):
            convert.convert_vwdb(str(db))


# ---------------------------------------------------------------------------
# real Xcelium, when present
# ---------------------------------------------------------------------------

def test_real_xcelium_vwdb(tmp_path, monkeypatch):
    monkeypatch.delenv("VWDB2VCD_BIN", raising=False)
    if convert.resolve_vwdb2vcd() is None or not shutil.which("xrun"):
        pytest.skip("Xcelium (xrun + vwdb2vcd) not available")
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
    env = dict(os.environ, CDNS_ENABLE_SHM2VWDB="1")
    proc = subprocess.run(["xrun", "-q", "-access", "+r", "tb.sv"],
                          cwd=tmp_path, capture_output=True, text=True,
                          timeout=600, env=env)
    dbs = [os.path.join(tmp_path, "waves.shm", n)
           for n in os.listdir(tmp_path / "waves.shm")
           if n.endswith(".vwdb")] if (tmp_path / "waves.shm").is_dir() else []
    if proc.returncode != 0 or not dbs:
        pytest.skip(f"xrun could not dump VWDB here: {proc.stdout[-300:]}")
    got = convert.resolve_waveform(dbs[0])
    assert got["kind"] == "vwdb"
    assert os.path.dirname(got["fst_path"]) == str(tmp_path)
    from pylibfst import ffi, lib
    ctx = lib.fstReaderOpen(got["fst_path"].encode())
    assert ctx != ffi.NULL
    lib.fstReaderClose(ctx)
