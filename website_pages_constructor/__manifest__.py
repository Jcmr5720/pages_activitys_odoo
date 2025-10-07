{
    'name': 'website_pages_constructor',
    'summary': 'Modulo encargado del constructor de pc.',
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
        'website_pages_controlador',
    ],
    'data': [
        'views/templates_constructor.xml',

        'views/constructor/main.xml',
        'views/report_saleorder.xml',
        #'data/data_website.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            ('include', 'web._assets_bootstrap'),
            'website_pages_constructor/static/src/scss/pc_builder.scss',
            'website_pages_constructor/static/src/js/pc_builder.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'GPL-3'
}