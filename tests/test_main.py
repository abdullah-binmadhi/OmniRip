from harvester.__main__ import main


def test_version_flag_exits_cleanly(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert "OmniRip" in capsys.readouterr().out


def test_enhance_cli_nonexistent_file(capsys):
    ret = main(["--enhance", "/nonexistent/path/song.mp3"])
    assert ret == 1
    err = capsys.readouterr().err
    assert "file not found" in err


def test_enhance_cli_unknown_preset(tmp_path, capsys):
    dummy = tmp_path / "test.mp3"
    dummy.write_bytes(b"dummy")
    ret = main(["--enhance", str(dummy), "--preset", "nonexistent_preset"])
    assert ret == 1
    err = capsys.readouterr().err
    assert "unknown preset" in err
