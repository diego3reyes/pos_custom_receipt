/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

/**
 * Datos del ticket que solo existen en el backend: el DTE (tipo, sello, número
 * de control) y los campos de la ficha del cliente que el POS no lleva
 * cargados. Se piden por RPC antes de renderizar para que la construcción del
 * contexto de la plantilla siga siendo síncrona.
 */

// Si el backend tarda más que esto se imprime sin estos datos: antes el ticket
// en la mano del cliente que una pantalla esperando.
const FETCH_TIMEOUT_MS = 3000;

// Cache por orden: una reimpresión no vuelve a preguntar por un DTE ya emitido.
const _cache = new Map();

/** Cadena imprimible: nunca "undefined", "null" ni "[object Object]". */
export function asText(value) {
    if (value === null || value === undefined || value === false) {
        return "";
    }
    if (typeof value === "object") {
        return asText(value.display_name ?? value.name ?? "");
    }
    return String(value);
}

/** Dirección legible a partir de los campos que el POS sí tiene del partner. */
export function partnerAddress(partner) {
    if (!partner) {
        return "";
    }
    return [
        asText(partner.street),
        asText(partner.street2),
        asText(partner.city),
        asText(partner.state_id),
        asText(partner.zip),
        asText(partner.country_id),
    ].filter(Boolean).join(", ");
}

/**
 * Lee del backend el contexto extra de una orden ya sincronizada.
 * Devuelve null (nunca lanza) si la orden no está en el servidor, si el RPC
 * falla o si tarda demasiado: la plantilla usa entonces valores vacíos.
 */
export async function fetchReceiptExtra(orderId) {
    // Una orden que todavía no se sincronizó lleva un id local ("pos.order_3"):
    // no existe en el servidor, así que no hay nada que preguntar.
    const id = Number(orderId);
    if (!Number.isInteger(id) || id <= 0) {
        return null;
    }
    if (_cache.has(id)) {
        return _cache.get(id);
    }

    let result = null;
    try {
        result = await Promise.race([
            rpc("/web/dataset/call_kw", {
                model: "pos.order",
                method: "pcr_get_receipt_extra",
                args: [[id]],
                kwargs: {},
            }),
            new Promise((resolve) => setTimeout(() => resolve(null), FETCH_TIMEOUT_MS)),
        ]);
    } catch (error) {
        console.warn("[pos_custom_receipt] No se pudo leer el DTE de la orden:", error);
        return null;
    }

    // Las claves del diccionario de Python llegan como cadenas por JSON-RPC.
    const extra = result ? (result[id] ?? result[String(id)] ?? null) : null;
    if (extra && extra.doc?.control_number && extra.doc?.seal) {
        // Solo se cachea el documento completo: el sello puede llegar después
        // del número de control, así que sin él la reimpresión vuelve a mirar.
        _cache.set(id, extra);
    }
    return extra;
}
