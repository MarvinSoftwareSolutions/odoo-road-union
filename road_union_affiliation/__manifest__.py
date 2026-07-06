# -*- coding: utf-8 -*-
{
    'name': "Sindicato vialidad - Afiliaciones",
    'summary': """
        Módulo de gestion gremial 
        de afiliados del sindicato de vialidad
        de la provincia de Córdoba.""",
    'author': "FMP solutions S.A.S.",
    'category': 'Union',
    'version': '1.0',
    "license": "AGPL-3",
    'depends': ['base', 'union_affiliation'],
    'assets': {
        'web.assets_backend': [
            'road_union_affiliation/static/src/scss/list_sticky.scss',
        ],
    },
    'data': [
        'views/affiliate_views.xml',
        'views/insurance_views.xml',
        'views/department_views.xml',
        'views/affiliate_old_db_views.xml',
        'views/affiliate_child_readonly_views.xml',
        'views/padrones_views.xml',
        'views/event_views.xml',
        'data/insurance_data.xml',
        'security/ir.model.access.csv',
    ],
    "installable": True,
}
