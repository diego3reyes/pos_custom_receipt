/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    createNewOrder(data = {}) {
        if (!data.partner_id) {
            const partnerId = this.config.default_partner_id?.id;
            if (partnerId) {
                const partner = this.models["res.partner"].find((p) => p.id === partnerId);
                if (partner) {
                    data = { ...data, partner_id: partner };
                }
            }
        }
        return super.createNewOrder(data);
    },
});
