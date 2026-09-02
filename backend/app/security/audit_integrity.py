from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Iterable


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


@dataclass(frozen=True)
class HashChainExport:
    lines: tuple[str, ...]
    root_sha256: str
    signature_hmac_sha256: str
    record_count: int


def build_hash_chain(records: Iterable[dict], *, signing_secret: bytes) -> HashChainExport:
    previous = "0" * 64
    lines: list[str] = []
    count = 0
    for record in records:
        payload = canonical_json(record)
        digest = hashlib.sha256(previous.encode("ascii") + payload).hexdigest()
        envelope = {"previous_sha256": previous, "record_sha256": digest, "record": record}
        lines.append(json.dumps(envelope, sort_keys=True, separators=(",", ":"), default=str))
        previous = digest
        count += 1
    signature = hmac.new(signing_secret, previous.encode("ascii"), hashlib.sha256).hexdigest()
    return HashChainExport(tuple(lines), previous, signature, count)


def verify_hash_chain(lines: Iterable[str], *, expected_root: str, expected_signature: str, signing_secret: bytes) -> bool:
    previous = "0" * 64
    for raw in lines:
        envelope = json.loads(raw)
        if envelope.get("previous_sha256") != previous:
            return False
        digest = hashlib.sha256(previous.encode("ascii") + canonical_json(envelope.get("record"))).hexdigest()
        if not hmac.compare_digest(digest, str(envelope.get("record_sha256", ""))):
            return False
        previous = digest
    if not hmac.compare_digest(previous, expected_root):
        return False
    signature = hmac.new(signing_secret, previous.encode("ascii"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected_signature)
