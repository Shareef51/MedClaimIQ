from app.sparse.provider import HashedBM25SparseEncoder


def test_sparse_encoder_is_stable_and_preserves_exact_medical_codes():
    encoder = HashedBM25SparseEncoder()
    first = encoder.encode_one("CPT 99213 prior authorization")
    second = encoder.encode_one("CPT 99213 prior authorization")
    assert first == second
    code = encoder.encode_one("99213")
    assert code.indices
    assert set(code.indices).issubset(set(first.indices))


def test_sparse_encoder_log_scales_repeated_term_frequency():
    encoder = HashedBM25SparseEncoder()
    one = encoder.encode_one("invoice")
    three = encoder.encode_one("invoice invoice invoice")
    assert one.indices == three.indices
    assert three.values[0] > one.values[0]
