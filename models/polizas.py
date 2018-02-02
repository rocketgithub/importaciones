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
    tipo_gasto_id = fields.Many2one('importaciones.tipo_gasto', string='Tipo de Gasto', ondelete='restrict')

class GastoAsociado(models.Model):
    _name = 'importaciones.gasto_asociado'
    _description = 'Gastos Proyectados Asociado'

    name = fields.Char(string='Descripción', required=True)
    poliza_id = fields.Many2one('importaciones.poliza', string='Poliza')
    valor = fields.Float('Valor', digits=dp.get_precision('Product Price'))
    tipo_gasto_id = fields.Many2one('importaciones.tipo_gasto', string='Tipo de gasto', ondelete='restrict')

class Poliza(models.Model):
    _name = 'importaciones.poliza'
    _description = 'Poliza'

    @api.model
    def convertir_precio(self, moneda_id, moneda_compra_id, moneda_base_id, tasa, fecha, precio):
        if moneda_id == moneda_compra_id:
            return precio * tasa
        else:
            return moneda_id.with_context(date=fecha).compute(precio, moneda_base_id)

    def generar_lineas(self):
        gasto_general = 0
        total_compras = 0
        for compra in self.compras_ids:
            moneda_compra = compra.currency_id.id

            if compra.gasto_general_poliza:
                for linea_compra in compra.order_line:
                    if linea_compra.product_id.type == 'service':
                        precio_convertido = self.convertir_precio(moneda_compra, self.moneda_compra_id, self.moneda_base_id, self.tasa, self.fecha, linea_compra.price_subtotal)
                        gasto_general += precio_convertido
            else:
                total_compras += compra.amount_total

        borrar = [(2, l.id) for l in self.lineas_ids]
        self.lineas_ids = borrar

        for compra in self.compras_ids:
            moneda_compra = compra.currency_id
            total_productos = 0
            gastos = 0
            if total_compras != 0:
                gastos = gasto_general * (compra.amount_total / total_compras);

            for linea_compra in compra.order_line:

                precio_convertido = self.convertir_precio(moneda_compra, self.moneda_compra_id, self.moneda_base_id, self.tasa, self.fecha, linea_compra.price_unit)

                if linea_compra.product_id.type == 'service':
                    gastos += precio_convertido * linea_compra.product_qty
                elif linea_compra.product_id.type == 'product':
                    total_productos += precio_convertido * linea_compra.product_qty

            for linea_compra in compra.order_line:
                logging.warn('3')

                if linea_compra.product_id.type != 'product':
                    continue

                precio_convertido = self.convertir_precio(moneda_compra, self.moneda_compra_id, self.moneda_base_id, self.tasa, self.fecha, linea_compra.price_unit)

                cantidad_recibida = linea_compra.product_qty

                gasto = ( ( ( precio_convertido * cantidad_recibida ) /  total_productos ) * gastos ) / cantidad_recibida
                precio_con_gastos = precio_convertido + gasto

                logging.warn(self.id)
                self.env['importaciones.poliza.linea'].create({
                    'poliza_id': self.id,
                    'producto_id': linea_compra.product_id.id,
                    'name': linea_compra.name,
                    'cantidad': cantidad_recibida,
                    'precio': precio_convertido,
                    'porcentage_gasto': gasto/precio_convertido*100,
                    'total_gastos': gasto,
                    'pedido': compra.id,
                })
        return True

    def asignar_gastos(self):
        for l in self.lineas_ids:
            l.gastos_ids = [(6, 0, [x.id for x in self.gastos_asociados_ids])]
        return True

    def asignar_facturas(self):
        for l in self.lineas_ids:
            l.documentos_ids = [(6, 0, [x.factura_id.id for x in self.documentos_asociados_ids])]
        return True

    def prorrateo_costo(self):
        documentos = {}
        gastos = {}
        arancel = {}

        for l in self.lineas_ids:
            # Ponderar documentos asociados
            for f in l.documentos_ids:
                if f.id not in documentos:
                    documentos[f.id] = 0
                documentos[f.id] += l.cantidad * l.precio

            # Ponderar gastos proyectados
            for g in l.gastos_ids:
                if g.id not in gastos:
                    gastos[g.id] = 0
                gastos[g.id] += l.cantidad * l.precio

        for l in self.lineas_ids:

            total_gastos = 0
            for f in l.documentos_ids:
                moneda_factura = f.currency_id

                total_convertido = self.convertir_precio(moneda_factura, self.moneda_compra_id, self.moneda_base_id, self.tasa, self.fecha, f.amount_untaxed)

                # El total de la linea dividido el total de todas las lineas
                # (que tengan esta factura asociada) por el total de la factura
                total_gastos += ((l.cantidad * l.precio) / documentos[f.id]) * total_convertido

            total_gastos_proyectados = 0
            for g in l.gastos_ids:
                total_gastos_proyectados += ((l.cantidad * l.precio) / gastos[g.id]) * g.valor

            impuestos = 0
            if l.cantidad != 0:
                impuestos = l.impuestos_importacion_manual / l.cantidad
            if len(l.impuestos_importacion_ids) > 0:
                precio = l.impuestos_importacion_ids.compute_all(l.precio + l.total_gastos)
                impuestos = precio['total_included'] - (l.precio + l.total_gastos)
            costo = (((l.precio + impuestos + l.total_gastos) * l.cantidad ) + total_gastos)/l.cantidad
            costo_proyectados = (((l.precio + impuestos + l.total_gastos) * l.cantidad ) + total_gastos_proyectados) / l.cantidad

            l.costo = costo
            l.costo_proyectado = costo_proyectados
            l.impuestos = impuestos
            l.costo_asignado = True

            if total_gastos > 0:
                l.total_gastos_importacion = total_gastos / l.cantidad
                l.porcentage_gasto_importacion = ( total_gastos + impuestos ) / ( l.precio * l.cantidad ) * 100
            else:
                l.total_gastos_importacion = total_gastos_proyectados / l.cantidad
                l.porcentage_gasto_importacion = ( total_gastos_proyectados + impuestos ) / ( l.precio * l.cantidad ) * 100

        # Ponderar arancel
        if self.arancel_total > 0:
            precio_total = 0
            for l in self.lineas_ids:
                precio_total += l.cantidad * l.precio

            for l in self.lineas_ids:
                arancel_real = (((l.cantidad * l.precio) / precio_total) * self.arancel_total) / l.cantidad
                diferencia = arancel_real - l.impuestos
                l.costo = l.costo + diferencia
                l.costo_proyectado = l.costo_proyectado + diferencia
                l.impuestos = arancel_real

        return True

    def asignar_costo_albaranes(self):
        for l in self.lineas_ids:
            costo = l.costo
            for c in self.compras_ids:
                for p in c.picking_ids:
                    for m in p.move_lines:
                        if m.product_id.id == l.producto_id.id:
                            m.price_unit = costo

            self.state = 'realizado'
        return True

    name = fields.Char(string='Descripción', required=True)
    fecha = fields.Date('Fecha', required=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.user.company_id)
    poliza_aduana = fields.Char('Poliza aduana')
    tipo_importacion = fields.Selection([('Aereo', 'Aereo'), ('Maritimo', 'Maritimo'), ('Terrestre', 'Terrestre')], string='Tipo de importación')
    guia = fields.Char('Guía/BL')
    transportista_id = fields.Many2one('res.partner', string='Transportista')
    comentario = fields.Text('Comentario')
    compras_ids = fields.One2many('purchase.order', 'poliza_id', string='Ordenes de compra', readonly=True)
    lineas_ids = fields.One2many('importaciones.poliza.linea', 'poliza_id', string='Lineas')
    gastos_asociados_ids = fields.One2many('importaciones.gasto_asociado', 'poliza_id', string='Gastos Asociados')
    documentos_asociados_ids = fields.One2many('importaciones.documento_asociado', 'poliza_id', string='Documentos Asociados')
    moneda_base_id = fields.Many2one('res.currency', string='Moneda de la Compañía', readonly=True, default=lambda self: self.env.user.company_id.currency_id)
    moneda_compra_id = fields.Many2one('res.currency', string='Moneda de la Compra', required=True)
    tasa = fields.Float('Tasa impuesta por SAT', digits=(12,6), required=True)
    arancel_total = fields.Float('Arancel total', digits=(12,6))
    state = fields.Selection( [('borrador','Borrador'), ('realizado','Realizado')], string='Status', required=True, readonly=True, copy=False, default='borrador')

class LineaPoliza(models.Model):
    _name = 'importaciones.poliza.linea'
    _description = 'Lineas de la Poliza'

    @api.multi
    @api.depends('costo_proyectado', 'costo')
    def _diferencia_costos(self):
        for linea in self:
            linea.diferencia_costos = linea.costo_proyectado - linea.costo

    @api.multi
    @api.depends('cantidad', 'precio', 'total_gastos')
    def _total_factura(self):
        for linea in self:
            linea.total_factura = linea.cantidad * ( linea.precio + linea.total_gastos)

    @api.multi
    @api.depends('costo', 'costo_proyectado', 'cantidad')
    def _total(self):
        for linea in self:
            if len(linea.documentos_ids) > 0:
                linea.total = linea.costo * linea.cantidad
            else:
                linea.total = linea.costo_proyectado * linea.cantidad

    name = fields.Text('Descripcion')
    poliza_id = fields.Many2one('importaciones.poliza', string='Poliza')
    producto_id = fields.Many2one('product.product', string='Producto', required=True)
    pedido = fields.Many2one('purchase.order', string='Pedido', required=True)
    cantidad = fields.Float('Cantidad', digits=dp.get_precision('Product Unit of Measure'), required=True)
    gastos_ids = fields.Many2many('importaciones.gasto_asociado', string='Gastos')
    documentos_ids = fields.Many2many('account.invoice', string='Facuras', domain=[('type','=','in_invoice')])
    impuestos_importacion_ids = fields.Many2many('account.tax', string='Aranceles', domain=[('type_tax_use','in',['purchase','all'])])
    impuestos_importacion_manual = fields.Float('Aranceles Manuales', digits=dp.get_precision('Product Price'))
    impuestos = fields.Float('Aranceles', digits=dp.get_precision('Product Price'))
    precio = fields.Float('Precio', digits=dp.get_precision('Product Price'), required=True)
    costo_proyectado = fields.Float('Costo unit. proyectado', digits=dp.get_precision('Product Price'))
    costo = fields.Float('Costo unit.', digits=dp.get_precision('Product Price'))
    diferencia_costos = fields.Float('Diferencia', digits=dp.get_precision('Product Price'), compute='_diferencia_costos')
    porcentage_gasto = fields.Float('% G. fact.', digits=dp.get_precision('Product Price'))
    porcentage_gasto_importacion = fields.Float('% G. imp.', digits=dp.get_precision('Product Price'))
    total_factura = fields.Float('Total pedido', digits=dp.get_precision('Product Price'), compute='_total_factura')
    total_gastos = fields.Float('G. fact.', digits=dp.get_precision('Product Price'))
    total_gastos_importacion = fields.Float('G. imp.', digits=dp.get_precision('Product Price'))
    total = fields.Float('Costo total', digits=dp.get_precision('Product Price'), compute='_total')
    costo_asignado = fields.Boolean('Costo asignado', readonly=True)
