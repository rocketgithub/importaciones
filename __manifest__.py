# -*- encoding: utf-8 -*-

{
    'name' : 'Importaciones',
    'version' : '1.0',
    'category': 'Custom',
    'description': """Modulo de importaciones de Prisma.""",
    'author': 'Rodrigo Fernández',
    'website': 'http://solucionesprisma.com/',
    'depends' : ['purchase_stock'],
    'demo' : [ ],
    'data' : [
        'views/polizas_view.xml',
        'views/report.xml',
        'views/poliza.xml',
        'views/purchase_view.xml',
        'security/ir.model.access.csv',
        'security/importaciones_security.xml',
    ],
    'installable': True,
}
