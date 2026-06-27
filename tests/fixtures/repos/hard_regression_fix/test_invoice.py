from invoice import invoice_total


def test_invoice_applies_discount():
    assert invoice_total(100) == 95
