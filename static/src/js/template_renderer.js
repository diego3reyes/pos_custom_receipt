/** @odoo-module **/

/**
 * Motor de plantillas simple tipo Jinja para el ticket del POS.
 * Soporta: {{ variable }}, {{ objeto.propiedad }}, {% if %}, {% for %}.
 */
export class TemplateRenderer {

    render(template, context) {
        if (!template) return '';
        let result = template;
        result = this._processForLoops(result, context);
        result = this._processIfBlocks(result, context);
        result = this._interpolateVariables(result, context);
        return result;
    }

    _interpolateVariables(template, context) {
        return template.replace(/\{\{\s*([\w.]+)\s*\}\}/g, (match, path) => {
            const value = this._getNestedValue(context, path);
            if (value === null || value === undefined) return '';
            return String(value);
        });
    }

    _getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => {
            return current !== null && current !== undefined ? current[key] : undefined;
        }, obj);
    }

    _processForLoops(template, context) {
        const forRegex = /\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}([\s\S]*?)\{%\s*endfor\s*%\}/g;
        return template.replace(forRegex, (match, itemVar, listVar, body) => {
            const list = context[listVar];
            if (!Array.isArray(list)) return '';
            return list.map(item => {
                const loopContext = { ...context, [itemVar]: item };
                return this.render(body, loopContext);
            }).join('');
        });
    }

    _processIfBlocks(template, context) {
        // Soporta {% if x %} y {% if not x %}
        const ifRegex = /\{%\s*if\s+(not\s+)?([\w.]+)\s*%\}([\s\S]*?)\{%\s*endif\s*%\}/g;
        return template.replace(ifRegex, (match, negation, path, body) => {
            const value = this._getNestedValue(context, path);
            const truthy = !!value;
            const condition = negation ? !truthy : truthy;
            return condition ? this.render(body, context) : '';
        });
    }
}
