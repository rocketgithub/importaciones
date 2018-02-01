# -*- encoding: utf-8 -*-

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    poliza_id = fields.Many2one('importaciones.poliza', string='Poliza', ondelete='restrict')
    gasto_general_poliza = fields.Boolean('Gastos Generales para Poliza')

    # # Modificado para que no incluya el IVA en el costo
    # def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):
    #     ''' prepare the stock move data from the PO line. This function returns a list of dictionary ready to be used in stock.move's create()'''
    #     product_uom = self.pool.get('product.uom')
    #     price_unit = order_line.price_subtotal / order_line.product_qty
    #     if order_line.product_uom.id != order_line.product_id.uom_id.id:
    #         price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor
    #     if order.currency_id.id != order.company_id.currency_id.id:
    #         #we don't round the price_unit, as we may want to store the standard price with more digits than allowed by the currency
    #         price_unit = self.pool.get('res.currency').compute(cr, uid, order.currency_id.id, order.company_id.currency_id.id, price_unit, round=False, context=context)
    #     res = []
    #     if order.location_id.usage == 'customer':
    #         name = order_line.product_id.with_context(dict(context or {}, lang=order.dest_address_id.lang)).name
    #     else:
    #         name = order_line.name or ''
    #     move_template = {
    #         'name': name,
    #         'product_id': order_line.product_id.id,
    #         'product_uom': order_line.product_uom.id,
    #         'product_uos': order_line.product_uom.id,
    #         'date': order.date_order,
    #         'date_expected': fields.date.date_to_datetime(self, cr, uid, order_line.date_planned, context),
    #         'location_id': order.partner_id.property_stock_supplier.id,
    #         'location_dest_id': order.location_id.id,
    #         'picking_id': picking_id,
    #         'partner_id': order.dest_address_id.id,
    #         'move_dest_id': False,
    #         'state': 'draft',
    #         'purchase_line_id': order_line.id,
    #         'company_id': order.company_id.id,
    #         'price_unit': price_unit,
    #         'picking_type_id': order.picking_type_id.id,
    #         'group_id': group_id,
    #         'procurement_id': False,
    #         'origin': order.name,
    #         'route_ids': order.picking_type_id.warehouse_id and [(6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
    #         'warehouse_id':order.picking_type_id.warehouse_id.id,
    #         'invoice_state': order.invoice_method == 'picking' and '2binvoiced' or 'none',
    #     }
    #
    #     diff_quantity = order_line.product_qty
    #     for procurement in order_line.procurement_ids:
    #         procurement_qty = product_uom._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, to_uom_id=order_line.product_uom.id)
    #         tmp = move_template.copy()
    #         tmp.update({
    #             'product_uom_qty': min(procurement_qty, diff_quantity),
    #             'product_uos_qty': min(procurement_qty, diff_quantity),
    #             'move_dest_id': procurement.move_dest_id.id,  #move destination is same as procurement destination
    #             'group_id': procurement.group_id.id or group_id,  #move group is same as group of procurements if it exists, otherwise take another group
    #             'procurement_id': procurement.id,
    #             'invoice_state': procurement.rule_id.invoice_state or (procurement.location_id and procurement.location_id.usage == 'customer' and procurement.invoice_state=='2binvoiced' and '2binvoiced') or (order.invoice_method == 'picking' and '2binvoiced') or 'none', #dropship case takes from sale
    #             'propagate': procurement.rule_id.propagate,
    #         })
    #         diff_quantity -= min(procurement_qty, diff_quantity)
    #         res.append(tmp)
    #     #if the order line has a bigger quantity than the procurement it was for (manually changed or minimal quantity), then
    #     #split the future stock move in two because the route followed may be different.
    #     if float_compare(diff_quantity, 0.0, precision_rounding=order_line.product_uom.rounding) > 0:
    #         move_template['product_uom_qty'] = diff_quantity
    #         move_template['product_uos_qty'] = diff_quantity
    #         res.append(move_template)
    #     return res
