"""Contexto extra del ticket: documento tributario (DTE) y ficha del cliente.

Solo lectura. El POS lo pide por RPC antes de renderizar porque el número de
control, el tipo y el sello viven únicamente en el backend (el objeto Order del
navegador no los trae).

No toca el objeto `dte` que publica la integración externa: lo que se agrega
aquí vive en su propio espacio, `doc`.
"""

import json

from odoo import models

from .pos_session import _dte_sort_key

# Etiquetas legibles cuando el sistema solo expone el código del tipo de DTE.
DTE_TYPE_LABELS = {
    '01': 'Factura',
    '03': 'Crédito Fiscal',
    '04': 'Nota de Remisión',
    '05': 'Nota de Crédito',
    '06': 'Nota de Débito',
    '07': 'Comprobante de Retención',
    '08': 'Comprobante de Liquidación',
    '11': 'Factura de Exportación',
    '14': 'Factura de Sujeto Excluido',
}

# Tipo del DTE: se prefiere el campo real del documento y, si no, el de la orden.
DTE_TYPE_FIELDS = ('type', 'dte_type', 'type_id', 'dte_type_id')
ORDER_TYPE_FIELDS = ('fl_l10n_sv_dte_type_id', 'fl_l10n_sv_dte_type')

# Giro / actividad económica del cliente: cada localización usa su propio campo,
# así que se toma el que exista en esta instalación en vez de inventar uno.
PARTNER_GIRO_FIELDS = (
    'giro',
    'giro_id',
    'l10n_sv_giro',
    'l10n_sv_giro_id',
    'fl_l10n_sv_giro',
    'fl_l10n_sv_giro_id',
    'economic_activity_id',
    'l10n_sv_economic_activity_id',
    'fl_l10n_sv_economic_activity_id',
    'l10n_sv_activity_id',
    'actividad_economica',
)

EMPTY_DOC = {'type': '', 'seal': '', 'control_number': ''}
EMPTY_CUSTOMER = {'giro': '', 'address': '', 'phone': '', 'email': ''}


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def pcr_get_receipt_extra(self):
        """{id: contexto} con lo que la plantilla del ticket no tiene en JS."""
        # Explícito antes de cualquier lectura con sudo del DTE: quien no puede
        # leer la orden tampoco ve su documento tributario.
        self.check_access('read')
        return {order.id: order._pcr_receipt_extra() for order in self}

    def _pcr_receipt_extra(self):
        self.ensure_one()
        return {
            'pos': {'name': _text(self.config_id.name)},
            'doc': self._pcr_doc(),
            'customer': self._pcr_customer(),
        }

    # ── doc: documento tributario electrónico ─────────────────────────────

    def _pcr_doc(self):
        """type / seal / control_number del DTE de esta orden. Nunca falla."""
        dte = self._pcr_dte()
        if dte is None:
            # Sin DTE emitido todavía el tipo puede venir de la propia orden.
            return dict(EMPTY_DOC, type=self._pcr_order_type_label())
        control_number = _text(_optional(dte, 'control_number'))
        return {
            'type': self._pcr_type_label(dte, control_number),
            'seal': _dte_seal(dte),
            'control_number': control_number,
        }

    def _pcr_dte(self):
        """El DTE que corresponde a esta orden, o None.

        Prefiere el que casa con el código de generación de la orden y descarta
        los anulados mientras quede alguno vigente; a igualdad, el más reciente,
        con el mismo criterio que el resumen del Corte Z.
        """
        self.ensure_one()
        documents = self._pcr_dte_documents()
        if not documents:
            return None

        live = documents.filtered(lambda d: not _optional(d, 'invalidated_at'))
        candidates = live or documents

        selected = candidates.browse()
        # En mayúsculas: el mismo UUID puede venir con distinto casing.
        generation_code = _text(_optional(self.sudo(), 'fl_l10n_sv_generation_code')).upper()
        if generation_code:
            selected = candidates.filtered(
                lambda d: _text(_optional(d, 'generation_code')).upper() == generation_code
            ).sorted(key=_dte_sort_key)[-1:]
        if not selected:
            # Sin coincidencia por código de generación: el más reciente.
            selected = candidates.sorted(key=_dte_sort_key)[-1:]
        return selected[0] if selected else None

    def _pcr_dte_documents(self):
        """DTE ligados a la orden, por la relación directa o por búsqueda.

        sudo: el cajero no siempre tiene lectura sobre el modelo del DTE, pero
        el sello y el número de control se imprimen en su ticket.
        """
        self.ensure_one()
        if 'fl_l10n_sv_dte_ids' in self._fields:
            return self.sudo().fl_l10n_sv_dte_ids
        if 'fl.l10n.sv.dte' not in self.env:
            return None
        dte_model = self.env['fl.l10n.sv.dte'].sudo()
        if 'pos_order_id' not in dte_model._fields:
            return None
        return dte_model.search([('pos_order_id', '=', self.id)])

    def _pcr_type_label(self, dte, control_number):
        """Tipo legible: campo del DTE, campo de la orden y, al final, prefijo."""
        for field_name in DTE_TYPE_FIELDS:
            label = _field_label(dte, field_name)
            if label:
                return label
        return self._pcr_order_type_label() or _type_from_control_number(control_number)

    def _pcr_order_type_label(self):
        """Tipo declarado en la propia orden, si el addon externo lo guarda."""
        self.ensure_one()
        for field_name in ORDER_TYPE_FIELDS:
            label = _field_label(self.sudo(), field_name)
            if label:
                return label
        return ''

    # ── customer: datos de la ficha que el POS no lleva cargados ──────────

    def _pcr_customer(self):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            return dict(EMPTY_CUSTOMER)
        return {
            'giro': _partner_giro(partner),
            'address': _partner_address(partner),
            'phone': _text(partner.phone) or _text(_optional(partner, 'mobile')),
            'email': _text(partner.email),
        }


# ── utilidades ────────────────────────────────────────────────────────────

def _text(value):
    """Cadena imprimible: nunca None, False ni un recordset vacío."""
    if not value:
        return ''
    return str(value).strip()


def _optional(record, field_name):
    """Lee un campo solo si existe en esta instalación."""
    return record[field_name] if field_name in record._fields else False


def _field_label(record, field_name):
    """Valor legible de un campo (selection, many2one o texto). '' si no aplica."""
    if record is None:
        return ''
    field = record._fields.get(field_name)
    if field is None:
        return ''
    value = record[field_name]
    if not value:
        return ''
    if field.type == 'many2one':
        return _text(value.display_name)
    if field.type == 'selection':
        description = record.fields_get([field_name]).get(field_name) or {}
        label = _text(dict(description.get('selection') or []).get(value))
        if label and label != _text(value):
            return label
        return _code_label(value) or label
    return _code_label(value) or _text(value)


def _code_label(value):
    """'01' → 'Factura'. Cadena vacía si no es un código de DTE conocido."""
    return DTE_TYPE_LABELS.get(_text(value), '')


def _type_from_control_number(control_number):
    """Último recurso: 'DTE-01-XXXX' → 'Factura'."""
    parts = _text(control_number).split('-')
    if len(parts) < 2:
        return ''
    return _code_label(parts[1])


def _dte_seal(dte):
    """response → mhResponse → data → selloRecibido. '' si falta cualquier paso."""
    response = _optional(dte, 'response')
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except ValueError:
            return ''
    if not isinstance(response, dict):
        return ''
    mh_response = response.get('mhResponse')
    if not isinstance(mh_response, dict):
        return ''
    data = mh_response.get('data')
    if not isinstance(data, dict):
        return ''
    return _text(data.get('selloRecibido'))


def _partner_giro(partner):
    """Giro / actividad económica, con el campo que use la localización."""
    field_name = next(
        (name for name in PARTNER_GIRO_FIELDS if name in partner._fields), '',
    )
    if not field_name:
        # Solo campos que de verdad se pueden imprimir: un booleano llamado
        # x_giro_ok saldría como "True" en el ticket.
        field_name = next(
            (
                name for name, field in sorted(partner._fields.items())
                if ('giro' in name or 'economic_activity' in name)
                and field.type in ('char', 'text', 'selection', 'many2one')
            ),
            '',
        )
    return _field_label(partner, field_name) if field_name else ''


def _partner_address(partner):
    """Dirección en una línea, con el formato del país cuando está disponible."""
    formatted = ''
    display_address = getattr(partner, '_display_address', None)
    if display_address:
        try:
            formatted = display_address(without_company=True) or ''
        except Exception:
            # Formato de dirección del país roto: se arma a mano más abajo.
            formatted = ''
    parts = [line.strip(' ,') for line in formatted.splitlines() if line.strip(' ,')]
    if not parts:
        parts = [
            _text(partner.street),
            _text(partner.street2),
            _text(partner.city),
            _text(partner.state_id.name),
            _text(partner.zip),
            _text(partner.country_id.name),
        ]
    return ', '.join(part for part in parts if part)
