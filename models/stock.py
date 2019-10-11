# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging

class Picking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def action_done(self):
        for l in self.move_lines:
            if l.purchase_line_id and l.purchase_line_id.order_id and l.purchase_line_id.order_id.poliza_id:
                if l.purchase_line_id.order_id.poliza_id.state != 'realizado':
                    raise UserError('Antes de poder transferir este documento debe de procesar la importación.')
        return super(Picking, self).action_done()

class StockMove(models.Model):
    _inherit = 'stock.move'

    # Version 10
    @api.multi
    def get_price_unit(self):
        self.ensure_one()
        if self.purchase_line_id and self.purchase_line_id.order_id and self.purchase_line_id.order_id.poliza_id:
            costo = 0
            for l in self.purchase_line_id.order_id.poliza_id.lineas_ids:
                if l.producto_id.id == self.product_id.id:
                    costo = l.costo
            return costo
        return super(StockMove, self).get_price_unit()

    # Version 11
    def _get_price_unit(self):
        self.ensure_one()
        if self.purchase_line_id and self.purchase_line_id.order_id and self.purchase_line_id.order_id.poliza_id:
            costo = 0
            for l in self.purchase_line_id.order_id.poliza_id.lineas_ids:
                if l.producto_id.id == self.product_id.id:
                    costo = l.costo
            return costo
        return super(StockMove, self)._get_price_unit()
