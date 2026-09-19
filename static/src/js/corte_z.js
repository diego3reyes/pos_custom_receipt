/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Component, markup } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { rpc } from "@web/core/network/rpc";

export class CorteZDialog extends Component {
    static components = { Dialog };
    static template = "pos_custom_receipt.CorteZDialog";
    static props = ["html", "sessionId", "close"];

    printReceipt() {
        // La página del servidor ya trae el CSS de 80mm y se auto-imprime al cargar.
        const iframe = document.createElement("iframe");
        iframe.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;";
        iframe.src = `/pos_custom_receipt/corte_z/${this.props.sessionId}`;
        document.body.appendChild(iframe);
        setTimeout(() => iframe.remove(), 10000);
    }
}

patch(ClosePosPopup.prototype, {
    async printCorteZ() {
        const sessionId = this.pos.session.id;
        let html;
        try {
            html = await rpc("/web/dataset/call_kw", {
                model: "pos.session",
                method: "get_corte_z_html",
                args: [[sessionId]],
                kwargs: {},
            });
        } catch (e) {
            console.error("[pos_custom_receipt] Error al generar el Corte Z:", e);
            this.dialog.add(AlertDialog, {
                title: "Corte Z",
                body: "No se pudo generar el Corte Z. Verifica la conexión con el servidor.",
            });
            return;
        }
        this.dialog.add(CorteZDialog, { html: markup(html), sessionId });
    },
});
