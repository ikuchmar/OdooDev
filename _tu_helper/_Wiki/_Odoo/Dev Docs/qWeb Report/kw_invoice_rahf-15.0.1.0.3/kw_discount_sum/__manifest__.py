{
    'name': 'Discount Sum',
    'summary': 'Discount Sum',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Accounting',
    'license': 'OPL-1',
    'version': '15.0.1.0.1',

    'depends': ['sale', 'account'],

    'data': [
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],

    'installable': True,

    'images': [
        'static/description/lib/cover.png',
        'static/description/lib/icon.png',
    ],

}
