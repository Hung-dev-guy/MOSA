from flask import g, request
from ..http import body, protected, respond
from backend.application import catalog_service
from backend.application import account_service
from backend.application import inventory_service
from backend.application import fulfillment_service
from backend.application import shipping_service
from backend.application import order_service
from backend.application import reporting_service
import csv
import io
from flask import Response
from flask import Blueprint
bp = Blueprint('administration_controller', __name__)


@bp.post('/api/staff/products')
@protected('admin')
def create_product():
    return respond(catalog_service.create_product(data=body(), user=g.user))


@bp.patch('/api/staff/products/<pid>')
@protected('admin')
def edit_product(pid):
    return respond(catalog_service.edit_product(pid, data=body(), user=g.user))


@bp.delete('/api/staff/products/<pid>')
@protected('admin')
def delete_product(pid):
    return respond(catalog_service.delete_product(pid, user=g.user))


@bp.patch('/api/staff/customers/<uid>')
@protected('admin')
def customer_status(uid):
    return respond(account_service.customer_status(uid, data=body(), user=g.user))


@bp.post('/api/staff/inventory')
@protected('warehouse')
def inventory():
    return respond(inventory_service.inventory(data=body(), user=g.user))


@bp.post('/api/staff/orders/<oid>/status')
@protected('warehouse')
def fulfil(oid):
    return respond(fulfillment_service.fulfil(oid, data=body(), user=g.user))


@bp.post('/api/staff/orders/<oid>/shipment')
@protected('sales')
def shipment(oid):
    return respond(shipping_service.shipment(oid, data=body(), user=g.user))


@bp.post('/api/staff/orders/<oid>/tracking')
@protected('sales')
def tracking(oid):
    return respond(shipping_service.tracking(oid, data=body(), user=g.user))


@bp.post('/api/staff/supply')
@protected('warehouse')
def supply():
    return respond(inventory_service.supply(data=body(), user=g.user))


@bp.post('/api/staff/supply/<rid>/receive')
@protected('warehouse')
def receive(rid):
    return respond(inventory_service.receive(rid, user=g.user))




@bp.patch('/api/staff/support/<cid>')
@protected('sales')
def resolve_case(cid):
    return respond(order_service.resolve_case(cid, data=body(), user=g.user))


@bp.post('/api/staff/exceptions')
@protected('sales')
def exception():
    return respond(order_service.exception(data=body(), user=g.user))


@bp.get('/api/staff/overview')
@protected('admin', 'warehouse', 'sales', 'manager')
def overview():
    return respond(order_service.overview(user=g.user))


@bp.get('/api/staff/reports')
@protected('manager')
def reports():
    return respond(reporting_service.report(query=request.args))


@bp.get('/api/staff/reports.csv')
@protected('manager')
def export_report():
    r = reporting_service.report(query=request.args)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['from_utc', 'to_exclusive_utc', 'generated_at', 'orders', 'paid_orders', 'revenue_vnd'])
    writer.writerow([r['from'], r['to_exclusive'], r['generated_at'], r['order_count'], r['paid_orders'], r['revenue']])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=mosa-report.csv'})
