from datetime import datetime

from markupsafe import escape

from odoo import _, fields, models
from odoo.tools import formatLang

from .template_renderer import render

# Clasificación de DTE (El Salvador) por prefijo del número de control.
# Solo estos dos entran al resumen del Corte Z.
DTE_SECTIONS = (
    ('fc', 'DTE-01-'),   # Factura
    ('ccf', 'DTE-03-'),  # Crédito Fiscal
)

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
            'dte_summary': self._corte_z_dte_summary(orders, money),
        }

    def _corte_z_datetime(self, value):
        if not value:
            return ''
        return fields.Datetime.context_timestamp(self, value).strftime('%d/%m/%Y %H:%M')

    # ── Resumen de DTE (opcional) ─────────────────────────────────────────
    # Solo lectura. Si el addon de facturación electrónica no está instalado,
    # los campos fl_l10n_sv_* no existen y el resumen sale vacío.

    def _corte_z_dte_summary(self, orders, money):
        summary = {
            key: {
                'count': 0, 'initial': '', 'final': '', 'total': money(0),
                'initial_generation_code': '', 'final_generation_code': '',
                'documents': [],
            }
            for key, _prefix in DTE_SECTIONS
        }

        order_fields = self.env['pos.order']._fields
        if 'fl_l10n_sv_dte_ids' not in order_fields:
            return summary

        has_approved_field = 'fl_l10n_sv_has_approved_dte' in order_fields
        has_generation_code = 'fl_l10n_sv_generation_code' in order_fields

        buckets = {key: [] for key, _prefix in DTE_SECTIONS}
        seen = set()

        for order in orders:
            if has_approved_field and not order.fl_l10n_sv_has_approved_dte:
                continue

            valid = order.fl_l10n_sv_dte_ids.filtered(
                lambda d: _dte_value(d, 'control_number') and not _dte_value(d, 'invalidated_at')
            )
            if not valid:
                continue

            dte = valid[:0]
            if has_generation_code and order.fl_l10n_sv_generation_code:
                # Si hay más de una coincidencia, la más reciente, igual que el fallback.
                dte = valid.filtered(
                    lambda d: _dte_value(d, 'generation_code') == order.fl_l10n_sv_generation_code
                ).sorted(key=_dte_sort_key)[-1:]
            if not dte:
                # Sin coincidencia por código de generación: el más reciente.
                dte = valid.sorted(key=_dte_sort_key)[-1:]

            dte = dte[0]
            if dte.id in seen:
                continue

            number = dte.control_number
            section = next((key for key, prefix in DTE_SECTIONS if number.startswith(prefix)), None)
            if not section:
                continue

            seen.add(dte.id)
            buckets[section].append((_dte_sort_key(dte), dte, order))

        for section, entries in buckets.items():
            if not entries:
                continue
            entries.sort(key=lambda entry: entry[0])
            summary[section] = {
                'count': len(entries),
                'initial': entries[0][1].control_number,
                'final': entries[-1][1].control_number,
                'initial_generation_code': _dte_value(entries[0][1], 'generation_code') or '',
                'final_generation_code': _dte_value(entries[-1][1], 'generation_code') or '',
                'total': money(sum(order.amount_total for _key, _dte, order in entries)),
                'documents': [
                    {
                        'number': dte.control_number,
                        'generation_code': _dte_value(dte, 'generation_code') or '',
                        'order': _order_reference(order),
                        'amount': money(order.amount_total),
                    }
                    for _key, dte, order in entries
                ],
            }
        return summary


def _dte_value(record, field_name):
    """Lee un campo del DTE solo si existe en esta instalación."""
    return record[field_name] if field_name in record._fields else False


def _dte_sort_key(dte):
    """Orden cronológico: generated_at, si no create_date, y el id como desempate."""
    stamp = _dte_value(dte, 'generated_at') or _dte_value(dte, 'create_date')
    return (stamp or datetime.min, dte.id)


def _order_reference(order):
    """'Order 265-1-004921' → '265-1-004921'; cualquier otra cosa queda igual."""
    reference = order.pos_reference or order.name or ''
    if reference.startswith('Order '):
        return reference[len('Order '):]
    return reference
