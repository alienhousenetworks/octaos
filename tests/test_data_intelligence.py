import io
import zipfile

import pytest
from fastapi import HTTPException

from app.api.v1.data_intelligence import _extract_zip, _profile, _read_table


def test_profile_reports_missingness_and_numeric_statistics():
    profile = _profile(
        ["amount", "region"],
        [
            {"amount": "10", "region": "east"},
            {"amount": "20", "region": ""},
            {"amount": "30", "region": "west"},
            {"amount": "", "region": None},
        ],
    )
    assert profile["row_count"] == 4
    assert profile["column_count"] == 2
    amount = next(field for field in profile["columns"] if field["name"] == "amount")
    assert amount["null_count"] == 1
    assert amount["min"] == 10
    assert amount["max"] == 30
    assert amount["mean"] == 20


def test_csv_parser_handles_utf8_bom_and_tsv():
    columns, rows = _read_table(b"\xef\xbb\xbfname,score\nA,2\nB,4\n", ".csv")
    assert columns == ["name", "score"]
    assert len(rows) == 2
    columns, rows = _read_table(b"name\tscore\nA\t2\n", ".tsv")
    assert columns == ["name", "score"]
    assert rows[0]["score"] == "2"


def test_zip_extracts_supported_files_and_ignores_unsupported():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("folder/sales.csv", "amount\n10\n")
        archive.writestr("folder/readme.exe", "not supported")
    files = _extract_zip(stream.getvalue(), "folder.zip")
    assert len(files) == 1
    assert files[0][0].endswith("folder/sales.csv")
    assert files[0][1] == b"amount\n10\n"


def test_zip_rejects_path_traversal():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("../outside.csv", "secret\n1")
    with pytest.raises(HTTPException) as exc:
        _extract_zip(stream.getvalue(), "unsafe.zip")
    assert exc.value.status_code == 400
