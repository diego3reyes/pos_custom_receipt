/** @odoo-module **/

/**
 * Formatea el número de ticket usando la configuración del POS.
 * @param {Object} config
 * @param {number} displayedSeq - Número ya calculado con base y offset aplicados
 * @returns {string|null}
 */
export function formatTicketNumber(config, displayedSeq) {
    const prefix = config.ticket_prefix || '';
    const suffix = config.ticket_suffix || '';
    const padding = config.ticket_padding || 6;

    if (!prefix && !suffix) return null;

    const padded = String(displayedSeq).padStart(padding, '0');
    return `${prefix}${padded}${suffix}`;
}

/**
 * Extrae el número secuencial del pos_reference de Odoo (ej: "261-1-000005" → 5).
 * @param {string} orderRef
 * @returns {number}
 */
export function extractInternalSeq(orderRef) {
    if (!orderRef) return 1;
    const parts = orderRef.split('-');
    return parseInt(parts[parts.length - 1]) || 1;
}

/**
 * Calcula el número a mostrar aplicando base y offset.
 * Formula: (internalSeq - base) + (startAt - 1)
 * Cuando base=0 y startAt=1: displayed = internalSeq (compatible hacia atrás).
 * @param {Object} config
 * @param {number} internalSeq
 * @returns {number}
 */
export function computeDisplayedSeq(config, internalSeq) {
    const base = config.ticket_sequence_base || 0;
    const startAt = config.ticket_next_number || 1;
    return (internalSeq - base) + (startAt - 1);
}

/**
 * Determina si el correlativo necesita reiniciarse según la configuración y la fecha actual.
 * @param {Object} config
 * @returns {boolean}
 */
export function needsSequenceReset(config) {
    const resetMode = config.ticket_reset_sequence;
    if (!resetMode || resetMode === 'never') return false;

    const today = new Date();
    const lastResetStr = config.ticket_sequence_last_reset;
    if (!lastResetStr) return true;

    const lastReset = new Date(lastResetStr);

    if (resetMode === 'yearly') {
        return lastReset.getFullYear() < today.getFullYear();
    }
    if (resetMode === 'monthly') {
        return (
            lastReset.getFullYear() < today.getFullYear() ||
            (lastReset.getFullYear() === today.getFullYear() &&
                lastReset.getMonth() < today.getMonth())
        );
    }
    return false;
}
