# POS — Ticket Personalizable y Correlativos

Módulo para **Odoo 19.0** (Community y Enterprise) que permite personalizar completamente el ticket del Punto de Venta.

## Funcionalidades

### Correlativo personalizable
- Prefijo y sufijo configurables (ej: `FAC-000001`)
- Número inicial, relleno con ceros (padding) y reinicio periódico (nunca / anual / mensual)

### Editor de plantilla HTML
- Edita el HTML del ticket directamente desde la configuración del POS
- Variables dinámicas con sintaxis `{{ variable }}`, `{% if %}`, `{% for %}`

### Apariencia del ticket
- Mostrar / ocultar cajero y cliente
- Mensaje de pie de página personalizable
- Ocultar branding de Odoo
- Ocultar etiqueta de impuesto por línea

### Cliente por defecto
- Asigna automáticamente un cliente a cada nueva orden del POS

### Corte Z
- Reporte de cierre de caja en formato 80 mm
- Incluye ventas, pagos por método y movimientos de caja (entradas/salidas)
- Botón de impresión desde el popup de cierre de sesión
- **Reimpresión de sesiones ya cerradas**: botón *Imprimir Corte Z* en **Punto de Venta → Sesiones → [sesión]**
- **Plantilla HTML editable** con la misma sintaxis que el ticket, compartida entre el POS y el backend
- Activable/desactivable desde la configuración

## Instalación

1. Copia la carpeta `pos_custom_receipt` en el directorio `addons` de tu instancia Odoo.
2. Actualiza la lista de módulos: **Ajustes → Técnico → Actualizar lista de módulos**.
3. Instala el módulo **POS — Ticket Personalizable y Correlativos**.
4. Configura las opciones en **Punto de Venta → Configuración → [Tu tienda] → Ticket Personalizable**.

## Compatibilidad

| Versión Odoo | Community | Enterprise |
|---|---|---|
| 19.0 | ✅ | ✅ |

## Variables disponibles en la plantilla

```
{{ company.name }}          Nombre de la empresa
{{ company.vat }}           NIT/RFC
{{ company.street }}        Dirección
{{ company.phone }}         Teléfono
{{ ticket.number }}         Número del ticket (con prefijo/sufijo)
{{ ticket.date }}           Fecha
{{ ticket.time }}           Hora
{{ ticket.cashier }}        Cajero
{{ customer.name }}         Cliente
{{ totals.subtotal }}       Subtotal
{{ totals.tax_amount }}     Impuesto
{{ totals.total }}          Total
{{ totals.change }}         Cambio
{{ config.footer_message }} Pie de página
```

## Variables disponibles en la plantilla del Corte Z

```
{{ company.name }}          Nombre de la empresa
{{ company.vat }}           NIT/RFC
{{ company.street }}        Dirección
{{ company.phone }}         Teléfono
{{ company.logo }}          Logo (data URI, para usar en <img src="...">)
{{ session.name }}          Nombre de la sesión (ej: POS/00042)
{{ session.config_name }}   Nombre de la caja / punto de venta
{{ session.cashier }}       Responsable de la sesión
{{ session.open_time }}     Fecha y hora de apertura
{{ session.close_time }}    Fecha y hora de cierre
{{ totals.orders_count }}   Tickets procesados
{{ totals.subtotal }}       Subtotal
{{ totals.tax_total }}      Impuesto
{{ totals.total }}          Total

{% for payment in payments %}{{ payment.name }} {{ payment.amount }}{% endfor %}
{% if cash_moves %}{% for move in cash_moves %}{{ move.name }} {{ move.amount }}{% endfor %}{% endif %}
```

Clases CSS disponibles: `row` (etiqueta a la izquierda, valor a la derecha),
`center`, `bold`, `big`.

## Licencia

LGPL-3
