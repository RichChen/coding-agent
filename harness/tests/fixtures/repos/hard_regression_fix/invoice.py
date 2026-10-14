from billing import discount


def invoice_total(subtotal):
    return discount(subtotal)
