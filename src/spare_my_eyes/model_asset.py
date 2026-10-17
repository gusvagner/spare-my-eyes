import hashlib
import os
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
MODEL_PATH = Path(__file__).parent / "assets" / "face_landmarker.task"
_CHUNK_BYTES = 1 << 20


class ModelIntegrityError(Exception):
    pass


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model(path: Path, expected_sha256: str = MODEL_SHA256) -> None:
    actual = sha256_of(path)
    if actual != expected_sha256:
        raise ModelIntegrityError(f"{path} has SHA-256 {actual}; expected {expected_sha256}")


def download_model(
    destination: Path = MODEL_PATH, url: str = MODEL_URL, expected_sha256: str = MODEL_SHA256
) -> None:
    if destination.is_file() and sha256_of(destination) == expected_sha256:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".download")
    urllib.request.urlretrieve(url, temporary)
    try:
        verify_model(temporary, expected_sha256)
    except ModelIntegrityError:
        temporary.unlink()
        raise
    os.replace(temporary, destination)


def main() -> None:
    download_model()
    print(f"Face landmarker model ready at {MODEL_PATH}")


if __name__ == "__main__":
    main()
