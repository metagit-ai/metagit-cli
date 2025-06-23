#!/usr/bin/env python
"""
Unit tests for metagit.core.utils.files
"""

from metagit.core.utils import files


def test_is_binary_file(tmp_path):
    # Create a text file
    text_file = tmp_path / "file.txt"
    text_file.write_text("hello world")
    assert files.is_binary_file(str(text_file)) is False
    # Create a binary file
    bin_file = tmp_path / "file.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03")
    assert files.is_binary_file(str(bin_file)) is True


def test_get_file_size(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("abc")
    assert files.get_file_size(str(f)) == 3
    assert files.get_file_size("/no/such/file") == 0


def test_list_files(tmp_path):
    (tmp_path / "a.txt").write_text("hi")
    (tmp_path / "b.txt").write_text("hi")
    files_list = files.list_files(str(tmp_path))
    assert any("a.txt" in f for f in files_list)
    assert any("b.txt" in f for f in files_list)
    assert files.list_files("/no/such/dir") == []


def test_read_file_lines(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("line1\nline2\n")
    lines = files.read_file_lines(str(f))
    assert lines == ["line1", "line2"]
    assert files.read_file_lines("/no/such/file") == []


def test_write_file_lines(tmp_path):
    f = tmp_path / "a.txt"
    files.write_file_lines(str(f), ["a", "b"])
    assert f.read_text() == "a\nb\n"


def test_copy_file(tmp_path):
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("hi")
    files.copy_file(str(src), str(dst))
    assert dst.read_text() == "hi"
    # Copy non-existent file
    assert files.copy_file("/no/such/file", str(dst)) is False


def test_remove_file(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hi")
    assert files.remove_file(str(f)) is True
    assert files.remove_file(str(f)) is False


def test_make_dir(tmp_path):
    d = tmp_path / "newdir"
    assert files.make_dir(str(d)) is True
    assert d.exists()
    # Already exists
    assert files.make_dir(str(d)) is True


def test_remove_dir(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    assert files.remove_dir(str(d)) is True
    assert files.remove_dir(str(d)) is False
