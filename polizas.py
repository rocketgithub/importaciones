# -*- encoding: utf-8 -*-

from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
import logging

class poliza(osv.osv):
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

                        precio_convertido = self.convertir_precio(cr, uid, moneda_compra, obj.moneda.id, obj.moneda_base.id, obj.tasa, obj.fecha, linea_compra.price_unit)

                        if linea_compra.product_id.type == 'service':
                            gasto_general += precio_convertido * linea_compra.product_qty
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

                self.pool.get('importaciones.poliza.linea').write(cr, uid, [l.id], {'costo': costo, 'costo_proyectado': costo_proyectados, 'impuestos': impuestos}, context)
                if total_gastos > 0:
                    self.pool.get('importaciones.poliza.linea').write(cr, uid, [l.id], {'total_gastos_importacion': total_gastos / l.cantidad, 'porcentage_gasto_importacion': ( total_gastos + impuestos ) / ( l.precio * l.cantidad ) * 100}, context)
                else:
                    self.pool.get('importaciones.poliza.linea').write(cr, uid, [l.id], {'total_gastos_importacion': total_gastos_proyectados / l.cantidad, 'porcentage_gasto_importacion': ( total_gastos_proyectados + impuestos ) / ( l.precio * l.cantidad ) * 100}, context)
        return True

    def asignar_costo_albaranes(self, cr, uid, ids, context={}):
        for obj in self.browse(cr, uid, ids, context):
            for l in obj.lineas:
                costo = l.costo_proyectado
                for o in obj.compras:
                    for p in o.picking_ids:
                        for m in p.move_lines:
                            if m.product_id.id == l.producto_id.id:
                                self.pool.get('stock.move').write(cr, uid, m.id, {'price_unit': costo})
        return True

    def _get_moneda_compania(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id

    _columns = {
        'name':fields.char('No. Poliza', size=64),
        'company_id': fields.many2one('res.company', "Compania", required=True),
        'poliza_aduana':fields.char('Poliza aduana', size=32),
        'tipo_importacion': fields.selection([('Aereo', 'Aereo'), ('Maritimo', 'Maritimo'), ('Terrestre', 'Terrestre')], 'Tipo de importación'),
        'guia':fields.char('Guía/BL', size=64),
        'transportista': fields.many2one('res.partner', "Transportista"),
        'comentario':fields.text('Comentario'),
        'fecha': fields.date('Fecha', required=True),
        'compras': fields.one2many('purchase.order', 'poliza_id', 'Ordenes de compra'),
        'lineas': fields.one2many('importaciones.poliza.linea', 'poliza_id', 'Lineas'),
        'gastos_proyectados': fields.one2many('importaciones.gastos_proyectados', 'poliza_id', 'Gastos asociados'),
        'documentos_asociados': fields.one2many('importaciones.documentos_asociados', 'poliza_id', 'Documentos asociados'),
        'moneda': fields.many2one('res.currency', 'Moneda de la compra', required=True),
        'moneda_base': fields.many2one('res.currency', 'Moneda de la compañía', readonly=True),
        'tasa': fields.float('Tasa impuesta por SAT', digits=(12,6), required=True),
    }

    _defaults = {
        'moneda_base': _get_moneda_compania,
    }

class linea_poliza(osv.osv):
    _name = 'importaciones.poliza.linea'
    _description = 'Las lineas con los productos de las ordenes de compra'

    def _diferencia_costos(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids, context=context):
            res[obj.id] = obj.costo_proyectado - obj.costo
        return res

    def _total_factura(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids, context=context):
            res[obj.id] = obj.cantidad * ( obj.precio + obj.total_gastos)
        return res

    def _total(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids, context=context):
            if len(obj.documentos) > 0:
                res[obj.id] = obj.costo * obj.cantidad
            else:
                res[obj.id] = obj.costo_proyectado * obj.cantidad
        return res

    _columns = {
        'poliza_id': fields.many2one('importaciones.poliza', 'Poliza', required=True),
        'producto_id': fields.many2one('product.product', 'Producto', required=True),
        'name': fields.text('Descripcion'),
        'pedido': fields.many2one('purchase.order', 'Pedido', required=True),
        'cantidad': fields.float('Cantidad', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'gastos': fields.many2many('importaciones.gastos_proyectados', 'poliza_linea_gasto_rel', 'poliza_linea', 'gasto', 'Gastos'),
        'documentos': fields.many2many('account.invoice', 'poliza_linea_factura_rel', 'poliza_linea', 'factura', 'Facuras', domain=[('type','=','in_invoice')]),
        'impuestos_importacion': fields.many2many('account.tax', 'poliza_impuestos_importacion_rel', 'prod_id', 'tax_id', 'Arancel calculado', domain=[('parent_id', '=', False),('type_tax_use','in',['purchase','all'])]),
        'impuestos_importacion_manual': fields.float('Arancel manual', digits_compute=dp.get_precision('Product Price')),
        'impuestos': fields.float('Arancel', digits_compute=dp.get_precision('Product Price')),
        'precio': fields.float('Precio', digits_compute=dp.get_precision('Product Price'), required=True),
        'costo_proyectado': fields.float('Costo unit. proyectado', digits_compute=dp.get_precision('Product Price')),
        'costo': fields.float('Costo unit.', digits_compute=dp.get_precision('Product Price')),
        'diferencia_costos': fields.function(_diferencia_costos, type='float', method=True, string='Diferencia', digits_compute=dp.get_precision('Product Price')),
        'porcentage_gasto': fields.float('% G. fact.', digits_compute=dp.get_precision('Product Price')),
        'porcentage_gasto_importacion': fields.float('% G. imp.', digits_compute=dp.get_precision('Product Price')),
        'total_factura': fields.function(_total_factura, type='float', method=True, string='Total pedido', digits_compute=dp.get_precision('Product Price')),
        'total_gastos': fields.float('G. fact.', digits_compute=dp.get_precision('Product Price')),
        'total_gastos_importacion': fields.float('G. imp.', digits_compute=dp.get_precision('Product Price')),
        'total': fields.function(_total, type='float', method=True, string='Costo total', digits_compute=dp.get_precision('Product Price')),
    }
