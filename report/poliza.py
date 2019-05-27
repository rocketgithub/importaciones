## -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, models, fields
import time
import logging

class ReportPoliza(models.AbstractModel):
    _name = 'report.importaciones.poliza'

    def gastos(self, o):
        gastos = []

        for p in o.compras_ids:
            linea = {
                'proveedor': p.partner_id.name,
                'pedido': p.name,
                'gasto': 0,
                'total': p.amount_total,
            }

            for l in p.order_line:
                if l.product_id.type == 'service':
                    linea['gasto'] += l.price_unit * l.product_qty

            gastos.append(linea)

        return gastos

    def facturas(self, o):
        facturas = []

        for d in o.documentos_asociados_ids:
            linea = {
                'proveedor': d.factura_id.partner_id.name,
                'factura': d.factura_id.reference,
                'total': d.factura_id.amount_total,
            }

            facturas.append(linea)

        return facturas

    def totales(self, o):
        totales = {
            'cantidad':0,
            'impuestos':0,
            'precio':0,
            'costo_proyectado':0,
            'costo':0,
            'total_factura':0,
            'total_gastos':0,
            'total_gastos_importacion':0,
            'total':0,
        }

        for l in o.lineas_ids:
            totales['cantidad'] += l.cantidad
            totales['impuestos'] += l.impuestos*l.cantidad
            totales['costo_proyectado'] += l.costo_proyectado*l.cantidad
            totales['costo'] += l.costo*l.cantidad
            totales['total_gastos'] += l.total_gastos*l.cantidad
            totales['total_gastos_importacion'] += l.total_gastos_importacion*l.cantidad

        return [totales]

    @api.model
    def _get_report_values(self, docids, data=None):
        self.model = 'importaciones.poliza'
        docs = self.env[self.model].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': self.model,
            'docs': docs,
            'time': time,
            'totales': self.totales,
            'gastos': self.gastos,
            'facturas': self.facturas,
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
