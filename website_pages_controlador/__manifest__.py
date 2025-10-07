{
    'name': 'website_pages_controlador',
    'summary': 'Modulo encargado de gestionar los modulos website_pages',
    'version': '1.0',
    'author': 'Juan Camilo Muñoz',
    'category': 'Tools',
    'depends': [
        'loyalty',
        'website',
        'web',
        'web_editor',
        'portal',
        'sale',
        'website_sale',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/website_page_views.xml',
        'views/menu_item_views.xml',
        'views/category_views.xml',
        'views/cotizacion_views.xml',
        'views/cotizacion_whatsapp_wizard_views.xml',
        'views/cotizacion_assign_wizard_views.xml',
        'views/cotizacion_assign_client_wizard_views.xml',
        'views/ajuste_views.xml',
        'views/category_rule.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            ('include', 'web._assets_bootstrap'),

        ],
        'web.assets_backend': [
            'website_pages_controlador/static/src/scss/category_rule.scss',
            'website_pages_controlador/static/src/scss/cotizacion.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'GPL-3'
}
