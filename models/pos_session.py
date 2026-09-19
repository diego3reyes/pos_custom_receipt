from markupsafe import escape

from odoo import _, fields, models
from odoo.tools import formatLang

from .template_renderer import render

# Mismo look que el ticket térmico de 80mm del POS.
CORTE_Z_CSS = """
@page { margin: 2mm; size: 80mm auto; }
body { font-family: 'Courier New', Courier, monospace; font-size: 11px;
       margin: 0; padding: 4mm; width: 72mm; color: #000; }
.row { display: flex; justify-content: space-between; }
.bold { font-weight: bold; }
.center { text-align: center; }
.big { font-size: 13px; font-weight: bold; }
hr { border: none; border-top: 1px dashed #000; margin: 3px 0; }
img { max-width: 100%; }
"""


class PosSession(models.Model):
    _inherit = 'pos.session'

    def action_print_corte_z(self):
        """Botón del formulario de sesión: abre el Corte Z imprimible."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/pos_custom_receipt/corte_z/%s' % self.id,
            'target': 'new',
        }

    def get_corte_z_html(self):
        """Fragmento HTML del Corte Z. Lo llama el POS por RPC y el controlador."""
        self.ensure_one()
        config = self.config_id
        template = config.corte_z_template or config._get_default_corte_z_template()
        return render(template, self._corte_z_context())

    def get_corte_z_page(self):
        """Página completa que se auto-imprime al abrirse."""
        self.ensure_one()
        return (
            '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
            '<title>Corte Z — %s</title><style>%s</style></head>'
            '<body onload="window.print()">%s</body></html>'
        ) % (escape(self.name or ''), CORTE_Z_CSS, self.get_corte_z_html())

    def _corte_z_context(self):
        self.ensure_one()
        currency = self.currency_id

        def money(amount):
            return formatLang(self.env, amount, currency_obj=currency)

        orders = self.order_ids.filtered(lambda o: o.state in ('paid', 'done', 'invoiced'))
        tax_total = sum(orders.mapped('amount_tax'))
        total = sum(orders.mapped('amount_total'))

        by_method = {}
        for payment in orders.mapped('payment_ids'):
            name = payment.payment_method_id.name or _('Sin método')
            by_method[name] = by_method.get(name, 0.0) + payment.amount

        # sudo: los usuarios de POS no siempre leen extractos bancarios.
        cash_moves = [
            {'name': line.payment_ref or _('Movimiento de caja'), 'amount': money(line.amount)}
            for line in self.sudo().statement_line_ids.sorted('create_date')
        ]

        company = self.company_id
        return {
            'company': {
                'name': company.name or '',
                'street': company.street or '',
                'phone': company.phone or '',
                'vat': company.vat or '',
                'logo': ('data:image/png;base64,%s' % company.logo.decode()) if company.logo else '',
            },
            'session': {
                'name': self.name or '',
                'config_name': self.config_id.name or '',
                'cashier': self.user_id.name or '',
                'open_time': self._corte_z_datetime(self.start_at),
                'close_time': self._corte_z_datetime(self.stop_at or fields.Datetime.now()),
            },
            'totals': {
                'orders_count': len(orders),
                'subtotal': money(total - tax_total),
                'tax_total': money(tax_total),
                'total': money(total),
            },
            'payments': [{'name': name, 'amount': money(amount)} for name, amount in by_method.items()],
            'cash_moves': cash_moves,
        }

    def _corte_z_datetime(self, value):
        if not value:
            return ''
        return fields.Datetime.context_timestamp(self, value).strftime('%d/%m/%Y %H:%M')
