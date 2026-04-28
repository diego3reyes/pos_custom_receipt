# CLAUDE.md — Plugin POS: Ticket Personalizable y Correlativos para Odoo 19
## `pos_custom_receipt` — Ticket Editable y Correlativos Configurables

---

## DESCRIPCIÓN DEL PROYECTO

Desarrollar un módulo genérico para **Odoo 19.0 (Community y Enterprise)** que permita a cualquier empresa:

1. **Configurar el correlativo del ticket** desde la interfaz — prefijo, número inicial, padding y más
2. **Editar la plantilla del ticket** directamente desde la interfaz usando código HTML
3. **Eliminar elementos no deseados** del ticket predeterminado de Odoo

Este módulo es de uso **genérico** — cualquier empresa que use Odoo POS puede instalarlo y configurarlo según sus necesidades sin tocar código fuente.

---

## CONTEXTO TÉCNICO IMPORTANTE

### Odoo 19 POS usa OWL (Owl.js)
En Odoo 17+ el ticket del POS fue migrado de QWeb a componentes **OWL (Owl Framework)**:
- ❌ NO se puede modificar desde **Ajustes → Técnico → Vistas**
- ✅ Se debe hacer override del componente JavaScript `OrderReceipt`
- ✅ El módulo proveerá un **editor de plantilla HTML** en la configuración del POS que se renderiza en el ticket

---

## FUNCIONALIDADES REQUERIDAS

### 1. Correlativo Personalizable

#### Problema actual
El número de ticket en Odoo 19 tiene el formato interno fijo:
```
{ID_CONFIG}-{ID_SESIÓN}-{NÚMERO}
```
Ejemplo: `261-1-000005` — no es configurable desde la interfaz.

#### Solución
Agregar en **POS → Configuración → [Tienda]** una sección completa de correlativo:

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `ticket_prefix` | Char | Prefijo del correlativo | `TD-` |
| `ticket_next_number` | Integer | Próximo número a usar | `1` |
| `ticket_padding` | Integer | Cantidad de dígitos con ceros | `6` |
| `ticket_suffix` | Char | Sufijo opcional al final | `` (vacío) |
| `ticket_reset_sequence` | Selection | Cuándo reiniciar el contador | Nunca / Anual / Mensual |
| `ticket_sequence_id` | Many2one | Secuencia de Odoo vinculada | (auto-generada) |

#### Formato resultante
```
[PREFIJO][NÚMERO_RELLENO][SUFIJO]
```

**Ejemplos según configuración:**

| Prefijo | Número | Padding | Sufijo | Resultado |
|---------|--------|---------|--------|-----------|
| `TD-` | 1 | 6 | `` | `TD-000001` |
| `FAC-` | 100 | 4 | `` | `FAC-0100` |
| `2026-` | 1 | 5 | `-A` | `2026-00001-A` |
| `` | 500 | 8 | `` | `00000500` |

#### Comportamiento
- El número incrementa automáticamente con cada venta confirmada
- El número visible en el ticket usa el formato configurado
- El número interno de Odoo **no se modifica** (compatibilidad)
- Si no se configura prefijo, se usa el número interno de Odoo como fallback
- Al cambiar `ticket_next_number` manualmente se puede reanudar desde cualquier número

---

### 2. Editor de Plantilla HTML del Ticket

#### Objetivo
Permitir que el usuario edite la plantilla del ticket directamente desde la interfaz de Odoo, sin necesidad de modificar archivos del servidor.

#### Cómo funciona
1. El módulo provee una **plantilla HTML base** con variables dinámicas
2. El usuario puede editar esa plantilla en un campo de texto en la configuración del POS
3. El ticket renderiza la plantilla con los datos reales de la venta
4. Si el campo está vacío, se usa la plantilla base del módulo

#### Campo en configuración
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `receipt_template` | Html / Text | Plantilla HTML del ticket |
| `use_custom_template` | Boolean | Activar plantilla personalizada |

#### Variables disponibles en la plantilla
El usuario puede usar estas variables en su HTML:

```
<!-- EMPRESA -->
{{ company.name }}          → Nombre de la empresa
{{ company.nit }}           → NIT (si l10n_sv está instalado)
{{ company.nrc }}           → NRC (si l10n_sv está instalado)
{{ company.street }}        → Dirección
{{ company.phone }}         → Teléfono
{{ company.email }}         → Email
{{ company.website }}       → Sitio web
{{ company.logo }}          → Logo (base64)
{{ company.giro }}          → Giro (si l10n_sv está instalado)

<!-- TICKET -->
{{ ticket.number }}         → Número del ticket (con prefijo)
{{ ticket.date }}           → Fecha de la venta
{{ ticket.time }}           → Hora de la venta
{{ ticket.cashier }}        → Nombre del cajero

<!-- CLIENTE -->
{{ customer.name }}         → Nombre del cliente
{{ customer.nit }}          → NIT del cliente
{{ customer.dui }}          → DUI del cliente

<!-- PRODUCTOS -->
{% for line in lines %}
  {{ line.quantity }}       → Cantidad
  {{ line.product_name }}   → Nombre del producto
  {{ line.unit_price }}     → Precio unitario
  {{ line.discount }}       → Descuento %
  {{ line.total_price }}    → Precio total de la línea
{% endfor %}

<!-- TOTALES -->
{{ totals.subtotal }}       → Subtotal sin IVA
{{ totals.tax_amount }}     → Monto del IVA
{{ totals.tax_name }}       → Nombre del impuesto (ej: IVA 13%)
{{ totals.total }}          → Total a pagar
{{ totals.amount_paid }}    → Monto pagado
{{ totals.change }}         → Cambio/vuelto

<!-- PAGOS -->
{% for payment in payments %}
  {{ payment.name }}        → Método de pago
  {{ payment.amount }}      → Monto
{% endfor %}

<!-- CONFIGURACIÓN DEL POS -->
{{ config.footer_message }} → Mensaje de pie de página
```

#### Plantilla base por defecto
El módulo incluye una plantilla HTML base que el usuario puede modificar:

```html
<div class="pos-receipt">

  <!-- ENCABEZADO -->
  <div class="receipt-header" style="text-align:center;">
    {% if company.logo %}
      <img src="{{ company.logo }}" style="max-width:150px; margin-bottom:8px;" />
    {% endif %}
    <div class="company-name"><strong>{{ company.name }}</strong></div>
    {% if company.nit %}
      <div>NIT: {{ company.nit }}</div>
    {% endif %}
    {% if company.nrc %}
      <div>NRC: {{ company.nrc }}</div>
    {% endif %}
    {% if company.giro %}
      <div>{{ company.giro }}</div>
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
  <div class="receipt-info">
    <div>Ticket: <strong>{{ ticket.number }}</strong></div>
    <div>Fecha: {{ ticket.date }} {{ ticket.time }}</div>
    {% if config.show_cashier and ticket.cashier %}
      <div>Cajero: {{ ticket.cashier }}</div>
    {% endif %}
    {% if config.show_customer and customer.name %}
      <div>Cliente: {{ customer.name }}</div>
    {% endif %}
  </div>

  <hr/>

  <!-- LÍNEAS DE PRODUCTOS -->
  <table class="receipt-lines" style="width:100%;">
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
  <div class="receipt-totals">
    <div style="display:flex; justify-content:space-between;">
      <span>Subtotal:</span>
      <span>{{ totals.subtotal }}</span>
    </div>
    <div style="display:flex; justify-content:space-between;">
      <span>{{ totals.tax_name }}:</span>
      <span>{{ totals.tax_amount }}</span>
    </div>
    <div style="display:flex; justify-content:space-between; font-weight:bold;">
      <span>TOTAL:</span>
      <span>{{ totals.total }}</span>
    </div>
  </div>

  <hr/>

  <!-- PAGOS -->
  {% for payment in payments %}
  <div style="display:flex; justify-content:space-between;">
    <span>{{ payment.name }}:</span>
    <span>{{ payment.amount }}</span>
  </div>
  {% endfor %}
  {% if totals.change > 0 %}
  <div style="display:flex; justify-content:space-between;">
    <span>Cambio:</span>
    <span>{{ totals.change }}</span>
  </div>
  {% endif %}

  <hr/>

  <!-- PIE DE PÁGINA -->
  {% if config.footer_message %}
  <div class="receipt-footer" style="text-align:center; margin-top:8px;">
    {{ config.footer_message }}
  </div>
  {% endif %}

</div>
```

---

### 3. Configuración General del Ticket

Agregar en **POS → Configuración → [Tienda]** una sección adicional:

| Campo | Tipo | Descripción | Predeterminado |
|-------|------|-------------|----------------|
| `ticket_footer_message` | Text | Mensaje de pie de página | `Gracias por su compra` |
| `show_cashier_on_ticket` | Boolean | Mostrar nombre del cajero | True |
| `show_customer_on_ticket` | Boolean | Mostrar nombre del cliente | True |
| `hide_odoo_branding` | Boolean | Ocultar "Con la tecnología de Odoo" | True |
| `hide_tax_on_lines` | Boolean | Ocultar etiqueta IVA por línea | True |
| `use_custom_template` | Boolean | Usar plantilla HTML personalizada | False |
| `receipt_template` | Text | Plantilla HTML personalizada | (plantilla base) |

---

## ESTRUCTURA DE ARCHIVOS

```
pos_custom_receipt/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   └── pos_config.py                        # Nuevos campos en pos.config
├── views/
│   └── pos_config_views.xml                 # Nueva sección en configuración POS
├── static/
│   └── src/
│       ├── overrides/
│       │   └── components/
│       │       └── receipt/
│       │           ├── CustomOrderReceipt.js    # Componente OWL personalizado
│       │           ├── CustomOrderReceipt.xml   # Template OWL
│       │           └── CustomOrderReceipt.scss  # Estilos base del ticket
│       └── js/
│           ├── template_renderer.js             # Motor de renderizado Jinja-like
│           └── ticket_sequence.js               # Lógica del correlativo
├── data/
│   └── pos_custom_receipt_data.xml              # Plantilla HTML base por defecto
├── security/
│   └── ir.model.access.csv
└── i18n/
    └── es.po
```

---

## MANIFEST

```python
{
    'name': 'POS — Ticket Personalizable y Correlativos',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Editor de ticket HTML y correlativos configurables para el POS',
    'description': '''
        Personaliza completamente el ticket del Punto de Venta en Odoo 19:
        - Editor de plantilla HTML del ticket desde la interfaz
        - Correlativo con prefijo, sufijo, padding y número inicial configurables
        - Opción para reinicio anual o mensual del correlativo
        - Ocultar branding de Odoo
        - Ocultar etiquetas de IVA por línea
        - Mensaje de pie de página personalizable
        - Compatible con Community y Enterprise
    ''',
    'author': '',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config_views.xml',
        'data/pos_custom_receipt_data.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_custom_receipt/static/src/overrides/components/receipt/CustomOrderReceipt.js',
            'pos_custom_receipt/static/src/overrides/components/receipt/CustomOrderReceipt.xml',
            'pos_custom_receipt/static/src/overrides/components/receipt/CustomOrderReceipt.scss',
            'pos_custom_receipt/static/src/js/template_renderer.js',
            'pos_custom_receipt/static/src/js/ticket_sequence.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
```

---

## MODELO `pos.config` — Campos adicionales

```python
from odoo import fields, models, api
from odoo.exceptions import ValidationError

class PosConfig(models.Model):
    _inherit = 'pos.config'

    # === CORRELATIVO ===
    ticket_prefix = fields.Char(
        string='Prefijo',
        default='',
        help='Texto que aparece antes del número. Ej: FAC- o TD-'
    )
    ticket_suffix = fields.Char(
        string='Sufijo',
        default='',
        help='Texto que aparece después del número. Opcional.'
    )
    ticket_next_number = fields.Integer(
        string='Próximo número',
        default=1,
        help='El próximo ticket usará este número'
    )
    ticket_padding = fields.Integer(
        string='Dígitos (relleno con ceros)',
        default=6,
        help='Cantidad de dígitos del número. Ej: 6 → 000001'
    )
    ticket_reset_sequence = fields.Selection([
        ('never', 'Nunca reiniciar'),
        ('yearly', 'Reiniciar cada año'),
        ('monthly', 'Reiniciar cada mes'),
    ], string='Reinicio del correlativo', default='never')

    # === APARIENCIA DEL TICKET ===
    ticket_footer_message = fields.Text(
        string='Mensaje de pie de página',
        default='Gracias por su compra'
    )
    show_cashier_on_ticket = fields.Boolean(
        string='Mostrar cajero',
        default=True
    )
    show_customer_on_ticket = fields.Boolean(
        string='Mostrar cliente',
        default=True
    )
    hide_odoo_branding = fields.Boolean(
        string='Ocultar "Con la tecnología de Odoo"',
        default=True
    )
    hide_tax_on_lines = fields.Boolean(
        string='Ocultar etiqueta de impuesto por línea',
        default=True
    )

    # === PLANTILLA PERSONALIZADA ===
    use_custom_template = fields.Boolean(
        string='Usar plantilla HTML personalizada',
        default=False
    )
    receipt_template = fields.Text(
        string='Plantilla HTML del ticket',
        help='Edita el HTML del ticket. Usa {{ variable }} para datos dinámicos.'
    )

    @api.constrains('ticket_padding')
    def _check_ticket_padding(self):
        for rec in self:
            if rec.ticket_padding < 1 or rec.ticket_padding > 10:
                raise ValidationError('El relleno debe estar entre 1 y 10 dígitos.')

    def _get_fields_for_pos_config(self):
        fields = super()._get_fields_for_pos_config()
        fields.extend([
            'ticket_prefix', 'ticket_suffix', 'ticket_next_number',
            'ticket_padding', 'ticket_reset_sequence', 'ticket_footer_message',
            'show_cashier_on_ticket', 'show_customer_on_ticket',
            'hide_odoo_branding', 'hide_tax_on_lines',
            'use_custom_template', 'receipt_template',
        ])
        return fields
```

---

## VISTA DE CONFIGURACIÓN POS

```xml
<!-- views/pos_config_views.xml -->
<record id="pos_config_view_form_custom_receipt" model="ir.ui.view">
    <field name="name">pos.config.view.form.custom.receipt</field>
    <field name="model">pos.config</field>
    <field name="inherit_id" ref="point_of_sale.pos_config_view_form"/>
    <field name="arch" type="xml">
        <xpath expr="//div[@name='pos_interface_configuration']" position="after">

            <!-- SECCIÓN CORRELATIVO -->
            <group string="Correlativo del Ticket" name="ticket_sequence_config">
                <group>
                    <field name="ticket_prefix" placeholder="Ej: FAC- o TD-"/>
                    <field name="ticket_suffix" placeholder="Opcional"/>
                    <field name="ticket_next_number"/>
                    <field name="ticket_padding"/>
                </group>
                <group>
                    <field name="ticket_reset_sequence"/>
                    <div class="text-muted" colspan="2">
                        Vista previa:
                        <strong>
                            [prefijo][000001][sufijo]
                        </strong>
                    </div>
                </group>
            </group>

            <!-- SECCIÓN APARIENCIA -->
            <group string="Apariencia del Ticket" name="ticket_appearance_config">
                <group>
                    <field name="ticket_footer_message"/>
                    <field name="show_cashier_on_ticket"/>
                    <field name="show_customer_on_ticket"/>
                </group>
                <group>
                    <field name="hide_odoo_branding"/>
                    <field name="hide_tax_on_lines"/>
                </group>
            </group>

            <!-- SECCIÓN PLANTILLA PERSONALIZADA -->
            <group string="Plantilla HTML del Ticket" name="ticket_template_config">
                <field name="use_custom_template"/>
                <field name="receipt_template"
                       widget="ace"
                       options="{'mode': 'html'}"
                       attrs="{'invisible': [('use_custom_template', '=', False)]}"
                       placeholder="Escribe aquí tu plantilla HTML personalizada..."/>
                <div attrs="{'invisible': [('use_custom_template', '=', False)]}">
                    <p class="text-muted">
                        Variables disponibles: {{ company.name }}, {{ ticket.number }},
                        {{ ticket.date }}, {{ ticket.cashier }}, {{ customer.name }},
                        {% for line in lines %} ... {% endfor %},
                        {{ totals.total }}, {{ config.footer_message }}
                    </p>
                </div>
            </group>

        </xpath>
    </field>
</record>
```

---

## MOTOR DE RENDERIZADO DE PLANTILLA

El archivo `template_renderer.js` implementa un motor simple de plantillas que soporta:

### Sintaxis soportada
```
{{ variable }}              → Interpolación de variable
{{ object.property }}       → Propiedad de objeto
{% if condición %}...{% endif %}    → Condicional
{% for item in lista %}...{% endfor %}  → Iteración
```

### Implementación básica
```javascript
// static/src/js/template_renderer.js

export class TemplateRenderer {
    render(template, context) {
        let result = template;

        // Procesar bloques for
        result = this._processForLoops(result, context);

        // Procesar bloques if
        result = this._processIfBlocks(result, context);

        // Interpolar variables {{ variable }}
        result = this._interpolateVariables(result, context);

        return result;
    }

    _interpolateVariables(template, context) {
        return template.replace(/\{\{\s*([\w.]+)\s*\}\}/g, (match, path) => {
            const value = this._getNestedValue(context, path);
            return value !== undefined ? value : '';
        });
    }

    _getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => {
            return current && current[key] !== undefined ? current[key] : undefined;
        }, obj);
    }

    _processForLoops(template, context) {
        const forRegex = /\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}([\s\S]*?)\{%\s*endfor\s*%\}/g;
        return template.replace(forRegex, (match, itemVar, listVar, body) => {
            const list = context[listVar] || [];
            return list.map(item => {
                const loopContext = { ...context, [itemVar]: item };
                return this.render(body, loopContext);
            }).join('');
        });
    }

    _processIfBlocks(template, context) {
        const ifRegex = /\{%\s*if\s+(.+?)\s*%\}([\s\S]*?)\{%\s*endif\s*%\}/g;
        return template.replace(ifRegex, (match, condition, body) => {
            const result = this._evaluateCondition(condition, context);
            return result ? this.render(body, context) : '';
        });
    }

    _evaluateCondition(condition, context) {
        const path = condition.trim();
        const value = this._getNestedValue(context, path);
        return !!value;
    }
}
```

---

## LÓGICA DEL CORRELATIVO

```javascript
// static/src/js/ticket_sequence.js

export function formatTicketNumber(config, internalNumber) {
    if (!config.ticket_prefix && !config.ticket_suffix) {
        return null; // Usar número interno de Odoo
    }

    const prefix = config.ticket_prefix || '';
    const suffix = config.ticket_suffix || '';
    const padding = config.ticket_padding || 6;
    const nextNumber = config.ticket_next_number || internalNumber;

    const paddedNumber = String(nextNumber).padStart(padding, '0');
    return `${prefix}${paddedNumber}${suffix}`;
}
```

---

## CONSIDERACIONES TÉCNICAS

### Compatibilidad
- Odoo 19.0 Community y Enterprise
- No requiere ningún módulo de localización
- Compatible con cualquier país y configuración

### Seguridad
- Solo usuarios con perfil **Gerente POS** pueden editar la plantilla HTML
- Sanitizar el HTML del template antes de renderizar para evitar XSS

### Performance
- La plantilla HTML se compila una sola vez al abrir la sesión POS
- Se cachea en el frontend para no recompilar en cada ticket

### Fallback
- Si `use_custom_template = False` → usar ticket predeterminado de Odoo con los ajustes de branding aplicados
- Si la plantilla tiene errores → mostrar mensaje de error y usar ticket predeterminado
- Si el prefijo está vacío → usar número interno de Odoo

### Editor de código
- Usar el widget `ace` de Odoo para el campo `receipt_template` con modo `html`
- Esto provee resaltado de sintaxis HTML directamente en la interfaz

---

## NOTAS PARA EL DESARROLLADOR

1. En Odoo 19 usar `patch()` de `@web/core/utils/patch` para override de componentes OWL
2. Los templates XML usan `t-inherit` con `t-inherit-mode="extension"`
3. Los assets se registran bajo `'point_of_sale._assets_pos'` en el manifest
4. El campo `receipt_template` debe enviarse al frontend mediante `_get_fields_for_pos_config()`
5. Probar con impresoras térmicas reales — el CSS del ticket debe ser compatible con impresión en 58mm y 80mm
6. El módulo NO debe romper el flujo normal del POS si hay algún error en la plantilla personalizada
