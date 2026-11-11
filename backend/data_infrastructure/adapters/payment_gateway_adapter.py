"""Demo gateway boundary; produces no external charge."""


def initial_payment(order_id,method,amount):
    return (order_id,method,'PENDING',f'MOSA-PAY-{order_id}',amount)
