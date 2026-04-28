{
    'name': 'POS — Ticket Personalizable y Correlativos',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Editor de ticket HTML y correlativos configurables para el POS',
    'description': '''
        Personaliza completamente el ticket del Punto de Venta en Odoo 19:
        - Editor de plantilla HTML del ticket desde la interfaz
        - Correlativo con prefijo, sufijo, padding y número inicial configurables
        - Ocultar branding de Odoo
        - Ocultar etiquetas de IVA por línea
        - Mostrar/ocultar cajero y cliente
        - Mensaje de pie de página personalizable
        - Compatible con Community y Enterprise
    ''',
    'author': '',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_custom_receipt/static/src/js/template_renderer.js',
            'pos_custom_receipt/static/src/js/ticket_sequence.js',
            'pos_custom_receipt/static/src/js/default_partner.js',
            'pos_custom_receipt/static/src/js/corte_z.js',
            'pos_custom_receipt/static/src/overrides/components/receipt/CorteZ.xml',
            'pos_custom_receipt/static/src/overrides/components/receipt/CorteZ.scss',
            'pos_custom_receipt/static/src/overrides/components/receipt/CustomOrderReceipt.js',
            'pos_custom_receipt/static/src/overrides/components/receipt/CustomOrderReceipt.xml',
            'pos_custom_receipt/static/src/overrides/components/receipt/CustomOrderReceipt.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
