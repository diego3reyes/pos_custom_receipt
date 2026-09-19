"""Motor de plantillas mínimo, equivalente a static/src/js/template_renderer.js.

Soporta {{ variable.ruta }}, {% if [not] variable %} y {% for x in lista %}.
Se usa en el servidor para que el Corte Z salga idéntico desde el POS y desde
el backend (una sola plantilla, un solo renderizador).
"""

import re

from markupsafe import escape

# ponytail: regex no-greedy → sin if anidados dentro de if. La plantilla por
# defecto no los usa; si algún día hacen falta, toca un parser de verdad.
_VAR_RE = re.compile(r'\{\{\s*([\w.]+)\s*\}\}')
_FOR_RE = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}([\s\S]*?)\{%\s*endfor\s*%\}')
_IF_RE = re.compile(r'\{%\s*if\s+(not\s+)?([\w.]+)\s*%\}([\s\S]*?)\{%\s*endif\s*%\}')


def render(template, context):
    if not template:
        return ''
    result = _render_for(template, context)
    result = _render_if(result, context)
    return _render_vars(result, context)


def _lookup(context, path):
    value = context
    for key in path.split('.'):
        value = value.get(key) if isinstance(value, dict) else getattr(value, key, None)
        if value is None:
            return None
    return value


def _render_vars(template, context):
    def replace(match):
        value = _lookup(context, match.group(1))
        # Los valores vienen de la BD (nombres de métodos de pago, empresa...),
        # así que se escapan: la plantilla es HTML, los datos no.
        return '' if value is None else str(escape(str(value)))
    return _VAR_RE.sub(replace, template)


def _render_for(template, context):
    def replace(match):
        item_var, list_var, body = match.groups()
        items = context.get(list_var)
        if not isinstance(items, (list, tuple)):
            return ''
        return ''.join(render(body, dict(context, **{item_var: item})) for item in items)
    return _FOR_RE.sub(replace, template)


def _render_if(template, context):
    def replace(match):
        negated, path, body = match.groups()
        truthy = bool(_lookup(context, path))
        return render(body, context) if (not truthy if negated else truthy) else ''
    return _IF_RE.sub(replace, template)


if __name__ == '__main__':
    ctx = {
        'company': {'name': 'Tienda & Cía', 'phone': None},
        'items': [{'n': 'Efectivo', 'v': '10'}, {'n': 'Tarjeta', 'v': '5'}],
        'empty': [],
    }
    assert render('', ctx) == ''
    assert render('{{ company.name }}', ctx) == 'Tienda &amp; Cía'
    assert render('{{ company.phone }}|{{ nope.x }}', ctx) == '|'
    assert render('{% if company.name %}sí{% endif %}', ctx) == 'sí'
    assert render('{% if company.phone %}no{% endif %}', ctx) == ''
    assert render('{% if not company.phone %}sí{% endif %}', ctx) == 'sí'
    assert render('{% if empty %}no{% endif %}', ctx) == ''
    assert render('{% for i in items %}{{ i.n }}={{ i.v }};{% endfor %}', ctx) == 'Efectivo=10;Tarjeta=5;'
    assert render('{% for i in empty %}x{% endfor %}', ctx) == ''
    assert render('{% for i in nope %}x{% endfor %}', ctx) == ''
    # for dentro de if: el for se procesa primero, igual que en el motor JS
    assert render('{% if items %}{% for i in items %}{{ i.n }},{% endfor %}{% endif %}', ctx) == 'Efectivo,Tarjeta,'
    print('template_renderer OK')
