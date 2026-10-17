import hashlib
from pathlib import Path

import pytest

from spare_my_eyes.model_asset import ModelIntegrityError, download_model, verify_model

CONTENT = b"model-bytes"
CONTENT_SHA256 = hashlib.sha256(CONTENT).hexdigest()


def write_source(tmp_path: Path) -> Path:
    source = tmp_path / "source.task"
    source.write_bytes(CONTENT)
    return source


def test_download_model_matching_hash_writes_destination(tmp_path: Path) -> None:
    destination = tmp_path / "assets" / "face_landmarker.task"
    download_model(destination, write_source(tmp_path).as_uri(), CONTENT_SHA256)
    assert destination.read_bytes() == CONTENT


def test_download_model_wrong_hash_raises_and_leaves_nothing(tmp_path: Path) -> None:
    destination = tmp_path / "assets" / "face_landmarker.task"
    with pytest.raises(ModelIntegrityError, match="expected"):
        download_model(destination, write_source(tmp_path).as_uri(), "0" * 64)
    assert not destination.exists()
    assert not destination.with_suffix(".download").exists()


def test_download_model_already_present_does_not_download(tmp_path: Path) -> None:
    destination = tmp_path / "face_landmarker.task"
    destination.write_bytes(CONTENT)
    unreachable = (tmp_path / "missing.task").as_uri()
    download_model(destination, unreachable, CONTENT_SHA256)
    assert destination.read_bytes() == CONTENT


def test_verify_model_mismatched_file_raises_with_both_hashes(tmp_path: Path) -> None:
    with pytest.raises(ModelIntegrityError, match=CONTENT_SHA256):
        verify_model(write_source(tmp_path), "f" * 64)
