 # -*- encoding: utf-8 -*-

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp

import logging

class TipoGasto(models.Model):
    _name = 'importaciones.tipo_gasto'
    _description = 'Tipos de Gastos'

    name = fields.Char(string='Descripción', required=True)

class DocumentoAsociado(models.Model):
    _name = 'importaciones.documento_asociado'
    _description = 'Documento Asociado'

    name = fields.Char(string='Descripción', required=True)
    poliza_id = fields.Many2one('importaciones.poliza', string='Poliza')
    factura_id = fields.Many2one('account.invoice', string='Documento', domain=[('type','=','in_invoice')])
    tipo_gasto_id = fields.Many2one('importaciones.tipo_gasto', string='Tipo de Gasto')

class GastoAsociado(models.Model):
    _name = 'importaciones.gasto_asociado'
    _description = 'Gastos Proyectados Asociado'

    name = fields.Char(string='Descripción', required=True)
    poliza_id = fields.Many2one('importaciones.poliza', string='Poliza')
    valor = fields.Float('Valor', digits_compute=dp.get_precision('Product Price'))
    tipo_gasto_id = fields.Many2one('importaciones.tipo_gasto', string='Tipo de gasto')

class Poliza(models.Model):
    _name = 'importaciones.poliza'

    def convertir_precio(self, cr, uid, moneda_compra_id, moneda_id, moneda_base_id, tasa, fecha, precio):
        if moneda_compra_id == moneda_id:
            return precio * tasa
        else:
            return self.pool.get('res.currency').compute(cr, uid, moneda_compra_id, moneda_base_id, precio, context={'date': fecha})

    def generar_lineas(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids):

            gasto_general = 0
            total_compras = 0
            for compra in obj.compras:
                moneda_compra = compra.currency_id.id

                if compra.gasto_general_poliza:
                    for linea_compra in compra.order_line:
                        if linea_compra.product_id.type == 'service':
                            precio_convertido = self.convertir_precio(cr, uid, moneda_compra, obj.moneda.id, obj.moneda_base.id, obj.tasa, obj.fecha, linea_compra.price_subtotal)
                            gasto_general += precio_convertido
                else:
                    total_compras += compra.amount_total

            for l in obj.lineas:
                self.pool.get('importaciones.poliza').write(cr, uid, [obj.id], {'lineas':[(2, l.id)]})

            for compra in obj.compras:
                moneda_compra = compra.currency_id.id
                total_productos = 0
                gastos = 0
                if total_compras != 0:
                    gastos = gasto_general * (compra.amount_total / total_compras);

                for linea_compra in compra.order_line:

                    precio_convertido = self.convertir_precio(cr, uid, moneda_compra, obj.moneda.id, obj.moneda_base.id, obj.tasa, obj.fecha, linea_compra.price_unit)

                    if linea_compra.product_id.type == 'service':
                        gastos += precio_convertido * linea_compra.product_qty
                    elif linea_compra.product_id.type == 'product':
                        total_productos += precio_convertido * linea_compra.product_qty

                for linea_compra in compra.order_line:

                    if linea_compra.product_id.type != 'product':
                        continue

                    precio_convertido = self.convertir_precio(cr, uid, moneda_compra, obj.moneda.id, obj.moneda_base.id, obj.tasa, obj.fecha, linea_compra.price_unit)

                    cantidad_recibida = linea_compra.product_qty

                    gasto = ( ( ( precio_convertido * cantidad_recibida ) /  total_productos ) * gastos ) / cantidad_recibida
                    precio_con_gastos = precio_convertido + gasto

                    self.pool.get('importaciones.poliza.linea').create(cr, uid, {
                        'poliza_id': obj.id,
                        'producto_id': linea_compra.product_id.id,
                        'name': linea_compra.name,
                        'cantidad': cantidad_recibida,
                        'precio': precio_convertido,
                        'porcentage_gasto': gasto/precio_convertido*100,
                        'total_gastos': gasto,
                        'pedido': compra.id,
                    })
        return True

    def asignar_gastos(self, cr, uid, ids, context={}):
        for obj in self.browse(cr, uid, ids, context):
            for l in obj.lineas:
                self.pool.get('importaciones.poliza.linea').write(cr, uid, [l.id], {'gastos':[(6, 0, [x.id for x in obj.gastos_proyectados])]})
        return True

    def asignar_facturas(self, cr, uid, ids, context={}):
        for obj in self.browse(cr, uid, ids, context):
            for l in obj.lineas:
                self.pool.get('importaciones.poliza.linea').write(cr, uid, [l.id], {'documentos':[(6, 0, [x.factura_id.id for x in obj.documentos_asociados])]})
        return True

    def prorrateo_costo(self, cr, uid, ids, context={}):
        for obj in self.browse(cr, uid, ids, context):
            documentos = {}
            gastos = {}
            arancel = {}

            # Ponderar documentos asociados
            for l in obj.lineas:
                for f in l.documentos:
                    if f.id not in documentos:
                        documentos[f.id] = 0
                    documentos[f.id] += l.cantidad * l.precio

            # Ponderar gastos proyectados
            for l in obj.lineas:
                for g in l.gastos:
                    if g.id not in gastos:
                        gastos[g.id] = 0
                    gastos[g.id] += l.cantidad * l.precio


            for l in obj.lineas:

                total_gastos = 0
                for f in l.documentos:
                    moneda_factura = f.currency_id.id

                    total_convertido = self.convertir_precio(cr, uid, moneda_factura, obj.moneda.id, obj.moneda_base.id, obj.tasa, obj.fecha, f.amount_untaxed)

                    # El total de la linea dividido el total de todas las lineas
                    # (que tengan esta factura asociada) por el total de la factura
                    total_gastos += ((l.cantidad * l.precio) / documentos[f.id]) * total_convertido

                total_gastos_proyectados = 0
                for g in l.gastos:
                    total_gastos_proyectados += ((l.cantidad * l.precio) / gastos[g.id]) * g.valor

                impuestos = 0
                if l.cantidad != 0:
                    impuestos = l.impuestos_importacion_manual / l.cantidad
                if len(l.impuestos_importacion) > 0:
                    precio = self.pool.get('account.tax').compute_all(cr, uid, l.impuestos_importacion, l.precio + l.total_gastos, 1)
                    impuestos = precio['total_included'] - (l.precio + l.total_gastos)
                costo = ( ( (l.precio + impuestos + l.total_gastos) * l.cantidad ) + total_gastos ) / l.cantidad
                costo_proyectados = ( ( (l.precio + impuestos + l.total_gastos) * l.cantidad ) + total_gastos_proyectados ) / l.cantidad

                self.pool.get('importaciones.poliza.linea').write(cr, uid, [l.id], {'costo': costo, 'costo_proyectado': costo_proyectados, 'impuestos': impuestos, 'costo_asignado': True}, context)
                if total_gastos > 0:
                    self.pool.get('importaciones.poliza.linea').write(cr, uid, [l.id], {'total_gastos_importacion': total_gastos / l.cantidad, 'porcentage_gasto_importacion': ( total_gastos + impuestos ) / ( l.precio * l.cantidad ) * 100}, context)
                else:
                    self.pool.get('importaciones.poliza.linea').write(cr, uid, [l.id], {'total_gastos_importacion': total_gastos_proyectados / l.cantidad, 'porcentage_gasto_importacion': ( total_gastos_proyectados + impuestos ) / ( l.precio * l.cantidad ) * 100}, context)

            # Ponderar arancel
            if obj.arancel_total > 0:
                precio_total = 0
                for l in obj.lineas:
                    precio_total += l.cantidad * l.precio

                for l in obj.lineas:
                    arancel_real = (((l.cantidad * l.precio) / precio_total) * obj.arancel_total) / l.cantidad
                    diferencia = arancel_real - l.impuestos
                    self.pool.get('importaciones.poliza.linea').write(cr, uid, [l.id], {'costo': l.costo + diferencia, 'costo_proyectado': l.costo_proyectado + diferencia, 'impuestos': arancel_real}, context)

        return True

    def asignar_costo_albaranes(self, cr, uid, ids, context={}):
        for obj in self.browse(cr, uid, ids, context):
            for l in obj.lineas:
                costo = l.costo
                for o in obj.compras:
                    for p in o.picking_ids:
                        for m in p.move_lines:
                            if m.product_id.id == l.producto_id.id:
                                self.pool.get('stock.move').write(cr, uid, m.id, {'price_unit': costo})

            self.write(cr, uid, [obj.id], {'state': 'realizado'}, context)
        return True

    def _get_moneda_compania(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id

    name = fields.Char(string='Descripción', required=True)
    fecha = fields.Date('Fecha', required=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.user.company_id)
    poliza_aduana = fields.Char('Poliza aduana')
    tipo_importacion = fields.Selection([('Aereo', 'Aereo'), ('Maritimo', 'Maritimo'), ('Terrestre', 'Terrestre')], string='Tipo de importación')
    guia = fields.Char('Guía/BL')
    transportista = fields.Many2one('res.partner', string='Transportista')
    comentario = fields.Text('Comentario')
    compras = fields.One2many('purchase.order', 'poliza_id', string='Ordenes de compra')
    lineas = fields.One2many('importaciones.poliza.linea', 'poliza_id', string='Lineas')
    gastos_proyectados_ids = fields.One2many('importaciones.gasto_asociado', 'poliza_id', string='Gastos Asociados')
    documentos_asociados_id = fields.One2many('importaciones.documento_asociado', 'poliza_id', string='Documentos Asociados')
    moneda_base = fields.Many2one('res.currency', string='Moneda de la Compañía', readonly=True, default=lambda self: self.env.user.company_id.currency_id)
    moneda_compra = fields.Many2one('res.currency', string='Moneda de la Compra', required=True)
    tasa = fields.Float('Tasa impuesta por SAT', digits=(12,6), required=True)
    arancel_total = fields.Float('Arancel total', digits=(12,6))
    state = fields.Selection( [('borrador','Borrador'), ('realizado','Realizado')], string='Status', required=True, readonly=True, copy=False, default='borrador')

class LineaPoliza(models.Model):
    _name = 'importaciones.poliza.linea'
    _description = 'Lineas de la Poliza'

    @api.one
    @api.depends('costo_proyectado', 'costo')
    def _diferencia_costos(self):
        self.diferencia_costos = self.costo_proyectado - self.costo

    @api.one
    @api.depends('cantidad', 'precio', 'total_gastos')
    def _total_factura(self):
        self.total_factura = self.cantidad * ( self.precio + self.total_gastos)

    @api.one
    @api.depends('costo', 'costo_proyectado', 'cantidad')
    def _total(self):
        if len(self.documentos) > 0:
            total = self.costo * self.cantidad
        else:
            total = self.costo_proyectado * self.cantidad

    poliza_id = fields.Many2one('importaciones.poliza', string='Poliza', required=True)
    producto_id = fields.Many2one('product.product', string='Producto', required=True)
    name = fields.Text('Descripcion')
    pedido = fields.Many2one('purchase.order', string='Pedido', required=True)
    cantidad = fields.Float('Cantidad', digits_compute=dp.get_precision('Product Unit of Measure'), required=True)
    gastos_ids = fields.Many2many('importaciones.gasto_asociado', string='Gastos')
    documentos_ids = fields.Many2many('account.invoice', string='Facuras', domain=[('type','=','in_invoice')])
    impuestos_importacion_ids = fields.Many2many('account.tax', string='Aranceles', domain=[('parent_id', '=', False),('type_tax_use','in',['purchase','all'])])
    impuestos_importacion_manual = fields.Float('Aranceles Manuales', digits_compute=dp.get_precision('Product Price'))
    impuestos = fields.Float('Aranceles', digits_compute=dp.get_precision('Product Price'))
    precio = fields.Float('Precio', digits_compute=dp.get_precision('Product Price'), required=True)
    costo_proyectado = fields.Float('Costo unit. proyectado', digits_compute=dp.get_precision('Product Price'))
    costo = fields.Float('Costo unit.', digits_compute=dp.get_precision('Product Price'))
    diferencia_costos = fields.Float('Diferencia', digits_compute=dp.get_precision('Product Price'), compute='_diferencia_costos')
    porcentage_gasto = fields.Float('% G. fact.', digits_compute=dp.get_precision('Product Price'))
    porcentage_gasto_importacion = fields.Float('% G. imp.', digits_compute=dp.get_precision('Product Price'))
    total_factura = fields.Float('Total pedido', digits_compute=dp.get_precision('Product Price'), compute='_total_factura')
    total_gastos = fields.Float('G. fact.', digits_compute=dp.get_precision('Product Price'))
    total_gastos_importacion = fields.Float('G. imp.', digits_compute=dp.get_precision('Product Price'))
    total = fields.Float('Costo total', digits_compute=dp.get_precision('Product Price'), compute='_total')
    costo_asignado = fields.Boolean('Costo asignado', readonly=True)
