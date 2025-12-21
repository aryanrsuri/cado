import hashlib


def hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
