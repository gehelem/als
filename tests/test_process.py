import numpy as np
from pytest import raises

from als.preprocess import get_limit_and_utype


def test_get_limit_and_utype_invalid():
    # the use of pytest.raises context manager allows to
    # that an expected exception is actually thrown
    with raises(ValueError):
        _, _ = get_limit_and_utype(np.array([0, 0, 0], dtype=np.float16))


def test_get_limit_and_utype_8bits():
    image = np.array([0, ], dtype=np.uint8)

    limit, type_string = get_limit_and_utype(image)

    true_limit = 2. ** 8 - 1
    true_type_string = "uint8"

    assert true_limit == limit
    assert true_type_string == type_string


def test_get_limit_and_utype_16bits():
    image = np.array([0, ], dtype=np.uint16)

    limit, type_string = get_limit_and_utype(image)

    true_limit = 2. ** 16 - 1
    true_type_string = "uint16"

    assert true_limit == limit
    assert true_type_string == type_string
