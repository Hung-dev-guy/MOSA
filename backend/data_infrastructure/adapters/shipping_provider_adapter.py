"""Staff-mediated carrier information; does not create a real carrier label."""
from backend.data_infrastructure.database.connection import now


def shipment_record(order_id,provider,tracking_code):
    return (order_id,provider,tracking_code,'in_transit',now())
