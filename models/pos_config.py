from odoo import fields, models, api
from odoo.exceptions import ValidationError

DEFAULT_CORTE_Z_TEMPLATE = """\
<div class="corte-z">

  <div class="center bold">{{ company.name }}</div>
  {% if company.vat %}<div class="center">NIT: {{ company.vat }}</div>{% endif %}
  {% if company.street %}<div class="center">{{ company.street }}</div>{% endif %}
  {% if company.phone %}<div class="center">Tel: {{ company.phone }}</div>{% endif %}

  <hr/>
  <div class="center big">*** CORTE Z ***</div>
  <hr/>

  <div class="row"><span>Sesión:</span><span>{{ session.name }}</span></div>
  <div class="row"><span>Caja:</span><span>{{ session.config_name }}</span></div>
  <div class="row"><span>Apertura:</span><span>{{ session.open_time }}</span></div>
  <div class="row"><span>Cierre:</span><span>{{ session.close_time }}</span></div>
  <div class="row"><span>Cajero:</span><span>{{ session.cashier }}</span></div>

  <hr/>
  <div class="row bold">
    <span>Tickets procesados:</span><span>{{ totals.orders_count }}</span>
  </div>

  <hr/>
  <div class="bold center">VENTAS</div>
  <div class="row"><span>Subtotal:</span><span>{{ totals.subtotal }}</span></div>
  <div class="row"><span>IVA:</span><span>{{ totals.tax_total }}</span></div>
  <div class="row bold big"><span>TOTAL:</span><span>{{ totals.total }}</span></div>

  <hr/>
  <div class="bold center">FORMA DE PAGO</div>
  {% for payment in payments %}
  <div class="row"><span>{{ payment.name }}:</span><span>{{ payment.amount }}</span></div>
  {% endfor %}

  {% if cash_moves %}
  <hr/>
  <div class="bold center">MOVIMIENTOS DE CAJA</div>
  {% for move in cash_moves %}
  <div class="row"><span>{{ move.name }}:</span><span>{{ move.amount }}</span></div>
  {% endfor %}
  {% endif %}

  {% if dte_summary.fc.documents %}
  <hr/>
  <div class="bold center">FACTURAS</div>
  <div class="row"><span>DTE Inicial:</span><span>{{ dte_summary.fc.initial }}</span></div>
  <div class="row"><span>DTE Final:</span><span>{{ dte_summary.fc.final }}</span></div>
  <div class="row"><span>Cantidad:</span><span>{{ dte_summary.fc.count }}</span></div>
  <div class="row bold"><span>Total:</span><span>{{ dte_summary.fc.total }}</span></div>
  {% endif %}

  {% if dte_summary.ccf.documents %}
  <hr/>
  <div class="bold center">CREDITOS FISCALES</div>
  <div class="row"><span>DTE Inicial:</span><span>{{ dte_summary.ccf.initial }}</span></div>
  <div class="row"><span>DTE Final:</span><span>{{ dte_summary.ccf.final }}</span></div>
  <div class="row"><span>Cantidad:</span><span>{{ dte_summary.ccf.count }}</span></div>
  <div class="row bold"><span>Total:</span><span>{{ dte_summary.ccf.total }}</span></div>
  {% endif %}

  <hr/>
  <div class="center">*** FIN DEL REPORTE ***</div>

</div>"""


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # === COMPORTAMIENTO ===
    show_corte_z = fields.Boolean(
        string='Mostrar botón Corte Z',
        default=True,
        help='Muestra el botón de Corte Z en el popup de cierre de sesión.',
    )
    default_partner_id = fields.Many2one(
        'res.partner',
        string='Cliente por defecto',
        help='Si se configura, cada nueva orden del POS comenzará con este cliente asignado.',
    )

    # === CORRELATIVO ===
    ticket_prefix = fields.Char(
        string='Prefijo',
        default='',
        help='Texto antes del número. Ej: FAC- o TD-',
    )
    ticket_suffix = fields.Char(
        string='Sufijo',
        default='',
        help='Texto después del número. Opcional.',
    )
    ticket_next_number = fields.Integer(
        string='Próximo número',
        default=1,
        help='El próximo ticket usará este número como base al inicio de sesión.',
    )
    ticket_padding = fields.Integer(
        string='Dígitos (relleno con ceros)',
        default=6,
        help='Cantidad de dígitos del número. Ej: 6 → 000001',
    )
    ticket_reset_sequence = fields.Selection([
        ('never', 'Nunca reiniciar'),
        ('yearly', 'Reiniciar cada año'),
        ('monthly', 'Reiniciar cada mes'),
    ], string='Reinicio del correlativo', default='never')
    ticket_sequence_last_reset = fields.Date(
        string='Último reinicio del correlativo',
    )
    ticket_sequence_base = fields.Integer(
        string='Base de secuencia interna',
        default=0,
        help='Número interno de Odoo en el momento del último reinicio.',
    )

    # === APARIENCIA DEL TICKET ===
    ticket_footer_message = fields.Text(
        string='Mensaje de pie de página',
        default='Gracias por su compra',
    )
    show_cashier_on_ticket = fields.Boolean(
        string='Mostrar cajero',
        default=True,
    )
    show_customer_on_ticket = fields.Boolean(
        string='Mostrar cliente',
        default=True,
    )
    hide_odoo_branding = fields.Boolean(
        string='Ocultar "Con la tecnología de Odoo"',
        default=True,
    )
    hide_tax_on_lines = fields.Boolean(
        string='Ocultar etiqueta de impuesto por línea',
        default=True,
    )

    # === PLANTILLA PERSONALIZADA ===
    use_custom_template = fields.Boolean(
        string='Usar plantilla HTML personalizada',
        default=False,
    )
    receipt_template = fields.Text(
        string='Plantilla HTML del ticket',
        help='Edita el HTML del ticket. Usa {{ variable }} para datos dinámicos.',
    )
    corte_z_template = fields.Text(
        string='Plantilla HTML del Corte Z',
        default=lambda self: DEFAULT_CORTE_Z_TEMPLATE,
        help='Edita el HTML del Corte Z. Si se deja vacío se usa la plantilla por defecto.',
    )

    def action_reset_corte_z_template(self):
        for rec in self:
            rec.corte_z_template = DEFAULT_CORTE_Z_TEMPLATE
        return True

    def _get_default_corte_z_template(self):
        return DEFAULT_CORTE_Z_TEMPLATE

    def apply_sequence_reset(self, new_base):
        """Called from POS frontend when a period reset is triggered."""
        self.ensure_one()
        self.write({
            'ticket_sequence_base': new_base,
            'ticket_sequence_last_reset': fields.Date.today(),
        })
        return True

    @api.onchange('use_custom_template')
    def _onchange_use_custom_template(self):
        if self.use_custom_template and not self.receipt_template:
            self.receipt_template = self._get_default_receipt_template()

    def _get_default_receipt_template(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'pos_custom_receipt.default_template'
        )
        if param:
            return param
        return """\
<div class="pos-receipt">

  <!-- ENCABEZADO -->
  <div style="text-align:center;">
    {% if company.logo %}
      <img src="{{ company.logo }}" style="max-width:150px; margin-bottom:8px;" />
    {% endif %}
    <div><strong>{{ company.name }}</strong></div>
    {% if company.vat %}
      <div>NIT: {{ company.vat }}</div>
    {% endif %}
    {% if company.street %}
      <div>{{ company.street }}</div>
    {% endif %}
    {% if company.phone %}
      <div>Tel: {{ company.phone }}</div>
    {% endif %}
  </div>

  <hr/>

  <!-- DATOS DEL TICKET -->
  <div>
    <div>Ticket: <strong>{{ ticket.number }}</strong></div>
    <div>Fecha: {{ ticket.date }} {{ ticket.time }}</div>
    {% if config.show_cashier %}
      <div>Cajero: {{ ticket.cashier }}</div>
    {% endif %}
    {% if config.show_customer %}
      <div>Cliente: {{ customer.name }}</div>
    {% endif %}
  </div>

  <hr/>

  <!-- PRODUCTOS -->
  <table style="width:100%;">
    {% for line in lines %}
    <tr>
      <td>{{ line.quantity }}</td>
      <td>{{ line.product_name }}</td>
      <td style="text-align:right;">{{ line.total_price }}</td>
    </tr>
    {% endfor %}
  </table>

  <hr/>

  <!-- TOTALES -->
  <div>
    <div style="display:flex; justify-content:space-between;">
      <span>Subtotal:</span><span>{{ totals.subtotal }}</span>
    </div>
    <div style="display:flex; justify-content:space-between;">
      <span>{{ totals.tax_name }}:</span><span>{{ totals.tax_amount }}</span>
    </div>
    <div style="display:flex; justify-content:space-between; font-weight:bold;">
      <span>TOTAL:</span><span>{{ totals.total }}</span>
    </div>
  </div>

  <hr/>

  <!-- PAGOS -->
  {% for payment in payments %}
  <div style="display:flex; justify-content:space-between;">
    <span>{{ payment.name }}:</span><span>{{ payment.amount }}</span>
  </div>
  {% endfor %}
  {% if totals.change %}
  <div style="display:flex; justify-content:space-between;">
    <span>Cambio:</span><span>{{ totals.change }}</span>
  </div>
  {% endif %}

  {% if config.footer_message %}
  <hr/>
  <div style="text-align:center;">{{ config.footer_message }}</div>
  {% endif %}

</div>"""

    @api.model
    def _cron_reset_ticket_sequences(self):
        """Cron diario: reinicia correlativos de tickets según configuración anual/mensual."""
        today = fields.Date.today()
        configs = self.search([('ticket_reset_sequence', '!=', 'never')])
        for config in configs:
            if not self._needs_sequence_reset(config, today):
                continue
            last_order = self.env['pos.order'].search(
                [('config_id', '=', config.id)],
                order='id desc', limit=1,
            )
            new_base = 0
            if last_order and last_order.pos_reference:
                parts = last_order.pos_reference.split('-')
                try:
                    new_base = int(parts[-1])
                except (ValueError, IndexError):
                    new_base = 0
            config.write({
                'ticket_sequence_base': new_base,
                'ticket_sequence_last_reset': today,
            })

    def _needs_sequence_reset(self, config, today):
        reset_mode = config.ticket_reset_sequence
        if not reset_mode or reset_mode == 'never':
            return False
        last_reset = config.ticket_sequence_last_reset
        if not last_reset:
            return True
        if reset_mode == 'yearly':
            return last_reset.year < today.year
        if reset_mode == 'monthly':
            return (
                last_reset.year < today.year or
                (last_reset.year == today.year and last_reset.month < today.month)
            )
        return False

    @api.constrains('ticket_padding')
    def _check_ticket_padding(self):
        for rec in self:
            if rec.ticket_padding < 1 or rec.ticket_padding > 10:
                raise ValidationError('El relleno debe estar entre 1 y 10 dígitos.')

    def _get_fields_for_pos_config(self):
        result = super()._get_fields_for_pos_config()
        result.extend([
            'show_corte_z',
            'default_partner_id',
            'ticket_prefix',
            'ticket_suffix',
            'ticket_next_number',
            'ticket_padding',
            'ticket_reset_sequence',
            'ticket_sequence_last_reset',
            'ticket_sequence_base',
            'ticket_footer_message',
            'show_cashier_on_ticket',
            'show_customer_on_ticket',
            'hide_odoo_branding',
            'hide_tax_on_lines',
            'use_custom_template',
            'receipt_template',
        ])
        return result
