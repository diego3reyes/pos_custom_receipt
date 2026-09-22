/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { markup, onMounted, onPatched, onWillStart } from "@odoo/owl";
import { TemplateRenderer } from "@pos_custom_receipt/js/template_renderer";
import { formatTicketNumber, extractInternalSeq, computeDisplayedSeq, needsSequenceReset } from "@pos_custom_receipt/js/ticket_sequence";
import { asText, fetchReceiptExtra, partnerAddress } from "@pos_custom_receipt/js/receipt_extra";
import { rpc } from "@web/core/network/rpc";

const _renderer = new TemplateRenderer();

// ── Patch ReceiptHeader: correlativo personalizado ────────────────────────
patch(ReceiptHeader.prototype, {
    get customTicketNumber() {
        const config = this.props.order?.config || {};
        const ref = this.props.order?.pos_reference || this.props.order?.name || '';
        const internalSeq = extractInternalSeq(ref);
        const displayedSeq = computeDisplayedSeq(config, internalSeq);
        return formatTicketNumber(config, displayedSeq);
    },
});

patch(OrderReceipt.prototype, {

    setup() {
        super.setup();
        this.receiptExtra = null;
        // El DTE y la ficha del cliente viven en el backend: se piden antes del
        // primer render (Owl espera a onWillStart) para que
        // _buildReceiptContext() siga siendo síncrono.
        onWillStart(async () => {
            this.receiptExtra = await this._loadReceiptExtra();
        });
        onMounted(() => {
            this._applyDynamicClasses();
            this._triggerSequenceResetIfNeeded();
        });
        onPatched(() => this._applyDynamicClasses());
    },

    async _loadReceiptExtra() {
        if (!this.useCustomTemplate) {
            return null;
        }
        return fetchReceiptExtra(this.order?.id);
    },

    _triggerSequenceResetIfNeeded() {
        const config = this._customConfig;
        if (!config || !config.id) return;
        if (config._sequenceResetChecked) return;
        config._sequenceResetChecked = true;

        if (!needsSequenceReset(config)) return;

        const ref = this.order?.pos_reference || this.order?.name || '';
        const lastInternalSeq = extractInternalSeq(ref);
        const newBase = Math.max(0, lastInternalSeq - 1);

        rpc('/web/dataset/call_kw', {
            model: 'pos.config',
            method: 'apply_sequence_reset',
            args: [[config.id], newBase],
            kwargs: {},
        }).then(() => {
            config.ticket_sequence_base = newBase;
            config.ticket_sequence_last_reset = new Date().toISOString().split('T')[0];
        }).catch((e) => {
            console.error('[PCR] Error al aplicar reinicio de secuencia:', e);
        });
    },

    _applyDynamicClasses() {
        if (!this.el) {
            return;
        }
        const receiptEl = this.el.classList?.contains("pos-receipt")
            ? this.el
            : this.el.querySelector(".pos-receipt");
        if (receiptEl) {
            receiptEl.classList.toggle("pcr-hide-branding", !!this.hideOdooBranding);
            receiptEl.classList.toggle("pcr-hide-tax-lines", !!this.hideTaxOnLines);
        }
    },

    // ── Acceso al config via order (Odoo 19) ─────────────────────────────
    get _customConfig() {
        return this.order?.config || {};
    },

    // ── Flags de configuración ────────────────────────────────────────────
    get useCustomTemplate() {
        return !!this._customConfig.use_custom_template;
    },

    get hideOdooBranding() {
        return !!this._customConfig.hide_odoo_branding;
    },

    get hideTaxOnLines() {
        return !!this._customConfig.hide_tax_on_lines;
    },

    // ── Número de ticket personalizado ────────────────────────────────────
    get customTicketNumber() {
        const config = this._customConfig;
        const orderName = this.order?.name || '';
        const internalSeq = extractInternalSeq(orderName);
        const displayedSeq = computeDisplayedSeq(config, internalSeq);
        return formatTicketNumber(config, displayedSeq);
    },

    // ── Renderizado de plantilla HTML personalizada ───────────────────────
    get renderedTemplate() {
        try {
            const config = this._customConfig;
            if (!config.use_custom_template || !config.receipt_template) {
                return markup('');
            }
            const context = this._buildReceiptContext();
            const html = _renderer.render(config.receipt_template, context);
            return markup(html);
        } catch (e) {
            console.error('[pos_custom_receipt] Error al renderizar plantilla:', e);
            return markup(
                `<div style="color:red;border:1px solid red;padding:8px;">
                    Error en plantilla: ${e.message}
                </div>`
            );
        }
    },

    // ── Construcción del contexto para la plantilla ───────────────────────
    _buildReceiptContext() {
        const order = this.order;
        const config = this._customConfig;
        const company = order.company || {};

        const orderDate = order.date_order ? new Date(order.date_order) : new Date();

        const orderlines = (order.lines || []).map(line => ({
            quantity: line.qty,
            product_name: line.full_product_name || line.product_id?.display_name || '',
            unit_price: this.formatCurrency(line.price_unit),
            discount: line.discount || 0,
            total_price: this.formatCurrency(line.price_subtotal_incl || 0),
            tax: line.taxGroupLabels || '',
        }));

        const paymentlines = (this.paymentLines || []).map(p => ({
            name: p.payment_method_id?.name || '',
            amount: this.formatCurrency(p.getAmount()),
        }));

        const ticketNumber = this.customTicketNumber || order.name || '';

        // Lo que vino del backend manda; si no llegó, se cae a lo que el POS
        // ya tiene cargado del partner y a cadenas vacías.
        const partner = order.partner_id || {};
        const extra = this.receiptExtra || {};
        const doc = extra.doc || {};
        const extraCustomer = extra.customer || {};

        return {
            pos: {
                name: asText(extra.pos?.name) || asText(config.name),
            },
            doc: {
                type: asText(doc.type),
                seal: asText(doc.seal),
                control_number: asText(doc.control_number),
            },
            company: {
                name: company.name || '',
                street: company.street || '',
                phone: company.phone || '',
                email: company.email || '',
                website: company.website || '',
                vat: company.vat || '',
                logo: company.logo ? `data:image/png;base64,${company.logo}` : null,
                nit: company.nit || null,
                nrc: company.nrc || null,
                giro: company.giro || null,
            },
            ticket: {
                number: ticketNumber,
                date: orderDate.toLocaleDateString(),
                time: orderDate.toLocaleTimeString(),
                cashier: order.getCashierName?.() || '',
            },
            customer: {
                name: order.partner_id?.name || '',
                nit: order.partner_id?.nit || null,
                dui: order.partner_id?.dui || null,
                giro: asText(extraCustomer.giro) || asText(partner.giro),
                address: asText(extraCustomer.address) || partnerAddress(partner),
                phone: asText(extraCustomer.phone) || asText(partner.phone) || asText(partner.mobile),
                email: asText(extraCustomer.email) || asText(partner.email),
            },
            lines: orderlines,
            totals: {
                subtotal: this.formatCurrency(order.priceExcl || 0),
                tax_amount: this.formatCurrency(
                    order.prices?.taxDetails
                        ? Object.values(order.prices.taxDetails).reduce((s, t) => s + (t.tax_amount_currency || 0), 0)
                        : 0
                ),
                tax_name: 'IVA',
                total: order.currencyDisplayPriceIncl || this.formatCurrency(0),
                amount_paid: this.formatCurrency(order.totalDue || 0),
                change: this.formatCurrency(order.change || 0),
            },
            payments: paymentlines,
            config: {
                footer_message: config.ticket_footer_message || '',
                show_cashier: config.show_cashier_on_ticket !== false,
                show_customer: config.show_customer_on_ticket !== false,
            },
        };
    },
});
