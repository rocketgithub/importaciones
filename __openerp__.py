# -*- encoding: utf-8 -*-

#
# Este es el modulo para toda la configuracion y funcionalidad de importaciones.
#
# Status 1.0 - tested on Open ERP 6.0.2
#

{
    'name' : 'Importaciones',
    'version' : '1.0',
    'category': 'Custom',
    'description': """Modulo de importaciones de Prisma.""",
    'author': 'Rodrigo Fernández',
    'website': 'http://solucionesprisma.com/',
    'depends' : ['purchase'],
    'demo' : [ ],
    'data' : [
        'polizas_view.xml',
        'purchase_view.xml',
        'catalogos_view.xml',
        'gastos_view.xml',
        #'res_company_view.xml',
        #'product_view.xml'
    ],
    'installable': True,
}
