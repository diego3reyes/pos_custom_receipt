/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";

const { DateTime } = luxon;

export class CorteZDialog extends Component {
    static components = { Dialog };
    static template = "pos_custom_receipt.CorteZDialog";
    static props = ["data", "close"];

    printReceipt() {
        const receiptEl = document.querySelector(".corte-z-receipt");
        if (!receiptEl) return;
        const iframe = document.createElement("iframe");
        iframe.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;";
        document.body.appendChild(iframe);
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        doc.open();
        doc.write(`<!DOCTYPE html><html><head><title>Corte Z</title>
        <style>
            @page { margin: 2mm; size: 80mm auto; }
            body { font-family: 'Courier New', Courier, monospace; font-size: 11px;
                   margin: 0; padding: 4mm; width: 72mm; color: #000; }
            .row { display: flex; justify-content: space-between; }
            .bold { font-weight: bold; }
            .center { text-align: center; }
            .big { font-size: 13px; font-weight: bold; }
            hr { border: none; border-top: 1px dashed #000; margin: 3px 0; }
        </style></head><body>${receiptEl.innerHTML}</body></html>`);
        doc.close();
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
        setTimeout(() => document.body.removeChild(iframe), 1000);
    }
}

patch(ClosePosPopup.prototype, {
    printCorteZ() {
        const fmt = (n) => this.env.utils.formatCurrency(n);

        const raw = this.pos.session.start_at;
        let openTime;
        try {
            openTime = raw
                ? DateTime.fromISO(raw).toFormat("dd/MM/yyyy HH:mm")
                : DateTime.now().toFormat("dd/MM/yyyy HH:mm");
        } catch (_) {
            openTime = String(raw || "").slice(0, 16);
        }

        const sessionOrders = this.pos.models["pos.order"].filter(
            (o) => o.session_id?.id === this.pos.session.id && o.finalized
        );
        const taxTotal = sessionOrders.reduce((s, o) => s + (o.amount_tax || 0), 0);
        const subtotal = this.props.orders_details.amount - taxTotal;

        const payments = [];
        if (this.props.default_cash_details) {
            payments.push({
                name: this.props.default_cash_details.name,
                amount: fmt(this.props.default_cash_details.amount),
            });
        }
        for (const pm of this.props.non_cash_payment_methods) {
            payments.push({ name: pm.name, amount: fmt(pm.amount) });
        }

        const cashMoves = (this.props.default_cash_details?.moves || []).map((m) => ({
            name: m.name,
            amount: fmt(m.amount),
        }));

        const data = {
            company_name: this.pos.company?.name || "",
            company_address: this.pos.company?.street || "",
            company_phone: this.pos.company?.phone || "",
            cashier: this.pos.user?.name || "",
            open_time: openTime,
            close_time: DateTime.now().toFormat("dd/MM/yyyy HH:mm"),
            orders_count: this.props.orders_details.quantity,
            total: fmt(this.props.orders_details.amount),
            subtotal: fmt(subtotal),
            tax_total: fmt(taxTotal),
            payments,
            cash_moves: cashMoves,
        };

        this.dialog.add(CorteZDialog, { data });
    },
});
