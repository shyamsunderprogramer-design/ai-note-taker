"""Stage document uploads in private, unique directories with bounded lifetime."""
from contextlib import contextmanager
from pathlib import Path
import shutil
import tempfile


class InvalidDocumentName(ValueError):
    """The supplied filename cannot be used safely as a single path component."""


@contextmanager
def staged_document(source, filename, upload_dir):
    if (
        not isinstance(filename, str)
        or not filename.strip()
        or len(filename.encode("utf-8")) > 255
        or ".." in filename
        or filename.endswith((".", " "))
        or any(char in '/\\<>:"|?*' or ord(char) < 32 or ord(char) == 127 for char in filename)
        or filename.split(".", 1)[0].upper() in {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10)),
        }
    ):
        raise InvalidDocumentName("Invalid filename")

    root = Path(upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    # TemporaryDirectory is private to this upload (0700 on POSIX). Retaining
    # the basename preserves document labels without collisions or symlinks in
    # the shared upload root. Both copy and ingestion failures leave this scope.
    with tempfile.TemporaryDirectory(prefix="document-", dir=root) as directory:
        path = Path(directory) / filename
        with path.open("xb") as destination:
            shutil.copyfileobj(source, destination)
        yield str(path)
