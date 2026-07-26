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
    'depends': ['base', 'base_automation',
                'union_affiliation', 'road_union_affiliation',
                'web_widget_x2many_2d_matrix'],
    'assets': {
        'web.assets_backend': [
            'road_union_economic_management/static/src/js/list_server_aggregates.js',
        ],
    },
    'post_init_hook': '_post_init_hook',
    'data': [
        'views/affiliate_class_basic_views.xml',
        'views/affiliate_class_basic_history_views.xml',
        'views/payment_account_current_views.xml',
        'security/ir.model.access.csv',
        'views/affiliate_views.xml',
        'wizards/payment_account_filter.xml',
        'wizards/meta_4_download.xml',
        'views/reports.xml',
        'views/provider_payments_views.xml',
        'views/pharmacies_views.xml',
        'views/pharmacy_discount_config_views.xml',
        'wizards/pharmacy_expense_import.xml',
        'views/automate_payment_creation_views.xml',
        'views/installment_plan_views.xml',
        'wizards/installment_plan_wizard.xml',
        'data/affiliate_class_basic_data.xml',
        'data/pharmacies_data.xml',
        'data/pharmacy_discount_config_data.xml',
        'views/menus_economia.xml',
    ],
    "installable": True,
}
