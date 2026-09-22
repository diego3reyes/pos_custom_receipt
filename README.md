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
{{ pos.name }}              Nombre del punto de venta (pos.config)
{{ customer.name }}         Cliente
{{ customer.giro }}         Giro / actividad económica del cliente
{{ customer.address }}      Dirección del cliente en una línea
{{ customer.phone }}        Teléfono del cliente
{{ customer.email }}        Correo del cliente
{{ doc.type }}              Tipo de DTE legible (ej: Factura, Crédito Fiscal)
{{ doc.control_number }}    Número de control del DTE
{{ doc.seal }}              Sello de recepción del Ministerio de Hacienda
{{ totals.subtotal }}       Subtotal
{{ totals.tax_amount }}     Impuesto
{{ totals.total }}          Total
{{ totals.change }}         Cambio
{{ config.footer_message }} Pie de página
```

`pos`, `doc` y los datos del cliente se leen del backend antes de imprimir
(número de control, tipo y sello no viajan en el objeto Order del navegador).
Si la orden aún no tiene DTE, todas estas variables quedan vacías y la
plantilla se imprime igual.

El objeto `dte` (`{{ dte.generation_code }}`, `{{ dte.qr_image }}`,
`{{ dte.verify_url }}`, `{{ dte.status }}`) lo publica la integración externa de
facturación electrónica; este módulo no lo modifica y usa su propio espacio,
`doc`, para no chocar con ella.

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
