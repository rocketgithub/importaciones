# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
import logging

class stock_picking(osv.osv):
    _inherit = "stock.picking"

    def do_enter_transfer_details(self, cr, uid, picking, context=None):
        p = self.browse(cr, uid, picking, context=context)
        for l in p.move_lines:
            if l.purchase_line_id and l.purchase_line_id.order_id and l.purchase_line_id.order_id.poliza_id:
                if l.purchase_line_id.order_id.poliza_id.state != 'realizado':
                    raise osv.except_osv('Error!', 'Antes de poder transferir este documento debe de procesar la importación.')
        return super(stock_picking, self).do_enter_transfer_details(cr, uid, picking, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
