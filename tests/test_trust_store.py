"""Guards the TLS trust store upstream connections are verified against (httpx uses certifi's bundle).

Python's ``ssl`` does not check revocation, so a root whose intermediates were compromised stays trusted until the
bundle drops it.
"""

import certifi


def test_trust_store_does_not_contain_compromised_emsign_root():
    assert "emSign ECC Root CA - G3" not in certifi.contents()
