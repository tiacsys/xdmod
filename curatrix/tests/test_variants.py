import gzip
import json

import pytest

from curatrix import model, variants
from helpers import FIXTURES


def check(name):
    data = json.loads(gzip.decompress((FIXTURES / "variants" / f"{name}.json.gz").read_bytes()))
    return variants.check(model.Model(data))


def test_robarm_product_line_is_ok():
    r = check("robarm")
    assert r.ok, r.errors
    assert set(r.configs) == {"prototype", "product"}
    assert len(r.variations) == 3
    assert any("controller = nucleoBreakouts" in n for n in r.notes)


@pytest.mark.parametrize("name,rules", [
    ("n1", {"V4", "V1"}),       # product PCBA in the prototype; second product model for 'prototype'
    ("n2", {"V3", "V1"}),       # bound to something that is not a variant
    ("n3", {"V2", "V1"}),       # variation not bound
    ("n4", {"V1"}),             # unknown configuration
    ("n6", {"F1", "F2", "V1"}), # two members of an xor group; constraint broken; no product model
])
def test_planted_errors(name, rules):
    r = check(name)
    assert not r.ok
    assert {e.split()[0] for e in r.errors} == rules, r.errors
