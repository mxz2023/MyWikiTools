import base64
import hashlib

from mi_fitness import signing


def test_signed_nonce_deterministic() -> None:
    ssecurity = base64.b64encode(b"secret-key-material-0123456789ab").decode()
    nonce = signing.generate_nonce(0)
    a = signing.signed_nonce(ssecurity, nonce)
    b = signing.signed_nonce(ssecurity, nonce)
    assert a == b
    assert signing.build_signature("GET", "/app/v1/x", {"data": "x"}, a)


def test_encrypt_roundtrip_structure() -> None:
    ssecurity = base64.b64encode(hashlib.sha256(b"test").digest()).decode()
    nonce = signing.generate_nonce(0)
    enc = signing.encrypt_query_params(
        method="GET",
        path="/app/v1/data/get_fitness_data_by_time",
        params={"data": "{}"},
        nonce=nonce,
        ssecurity=ssecurity,
    )
    assert "signature" in enc and "_nonce" in enc and enc["_nonce"] == nonce
