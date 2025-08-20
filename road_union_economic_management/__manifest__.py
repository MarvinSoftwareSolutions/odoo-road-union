# -*- coding: utf-8 -*-
{
    'name': "Sindicato vialidad - Gestión económica de afiliados",
    'summary': """
        Módulo de gestion económica 
        de afiliados del sindicato de vialidad
        de la provincia de Córdoba.""",
    'author': "FMP solutions S.A.S.",
    'category': 'Union',
    'version': '1.0',
    "license": "AGPL-3",
    'depends': ['base', 'union_affiliation', 'road_union_affiliation'],
    'data': [
        'views/payment_account_current_views.xml',
        'security/ir.model.access.csv',
        'views/affiliate_views.xml',
    ],
    "installable": True,
}
