from . import models, wizards
import logging

_logger = logging.getLogger(__name__)


def _post_init_hook(cr, registry):
    """
    Migración: crea registros de historial para todos los meses existentes
    usando los básicos actuales de cada clase.
    """
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    History = env['affiliate.class.basic.history']
    ClassBasic = env['affiliate.class.basic']
    PaymentAccount = env['affiliate.payment_account']

    all_classes = ClassBasic.search([], order='class_number asc')
    if not all_classes:
        return

    # Obtener meses/años distintos de payment_account
    cr.execute("""
        SELECT DISTINCT date_month, date_year
        FROM affiliate_payment_account
        ORDER BY date_year, date_month
    """)
    months = cr.fetchall()

    if not months:
        return

    _logger.info(f"post_init_hook: Creating history for {len(months)} months and {len(all_classes)} classes")

    first_month = True
    for date_month, date_year in months:
        for class_basic in all_classes:
            existing = History.search([
                ('class_basic_id', '=', class_basic.id),
                ('date_month', '=', date_month),
                ('date_year', '=', date_year),
            ], limit=1)

            if not existing:
                History.create({
                    'class_basic_id': class_basic.id,
                    'date_month': date_month,
                    'date_year': date_year,
                    'basic_amount': class_basic.basic_amount,
                    'manually_modified': first_month and class_basic.class_number == 1,
                })
        first_month = False

    _logger.info("post_init_hook: History records created successfully")
