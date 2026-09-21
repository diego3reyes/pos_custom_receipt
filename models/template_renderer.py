"""Motor de plantillas mínimo, hermano de static/src/js/template_renderer.js.

Soporta {{ variable.ruta }}, {% if [not] variable.ruta %} y
{% for x in lista.con.ruta %}, todos con rutas anidadas y bloques que se
pueden anidar entre sí en cualquier combinación.
Se usa en el servidor para que el Corte Z salga idéntico desde el POS y desde
el backend (una sola plantilla, un solo renderizador).

Los bloques se parsean con una pila, no con regex de emparejamiento: un regex
no-greedy casa el {% if %} externo con el {% endif %} interno y deja tags
sueltos impresos en el ticket.

Diferencia con el motor JS: aquí {% for %} y {% if %} aceptan rutas con punto
(p. ej. dte_summary.fc.documents) y anidamiento. El motor JS solo acepta un
nombre simple; no se toca para no alterar el ticket de venta, que es lo único
que lo usa.
"""

import re

from markupsafe import escape

_VAR_RE = re.compile(r'\{\{\s*([\w.]+)\s*\}\}')
_TAG_RE = re.compile(r'\{%\s*(?P<tag>if|for|endif|endfor)\b(?P<args>[^%]*?)\s*%\}')
_IF_ARGS_RE = re.compile(r'^(not\s+)?([\w.]+)$')
_FOR_ARGS_RE = re.compile(r'^(\w+)\s+in\s+([\w.]+)$')


def render(template, context):
    if not template:
        return ''
    return _render_nodes(_parse(template), context)


def _lookup(context, path):
    value = context
    for key in path.split('.'):
        value = value.get(key) if isinstance(value, dict) else getattr(value, key, None)
        if value is None:
            return None
    return value


def _render_vars(text, context):
    def replace(match):
        value = _lookup(context, match.group(1))
        # Los valores vienen de la BD (nombres de métodos de pago, empresa...),
        # así que se escapan: la plantilla es HTML, los datos no.
        return '' if value is None else str(escape(str(value)))
    return _VAR_RE.sub(replace, text)


def _parse(template):
    """Convierte la plantilla en un árbol de nodos respetando el anidamiento.

    Nodos: ('text', str) | ('if', negado, ruta, hijos) | ('for', var, ruta, hijos).
    Los tags mal formados o descolgados se descartan; nunca se imprimen.
    """
    root = []
    stack = [(None, root)]
    position = 0

    for match in _TAG_RE.finditer(template):
        if match.start() > position:
            stack[-1][1].append(('text', template[position:match.start()]))
        position = match.end()
        tag, args = match.group('tag'), match.group('args').strip()

        if tag == 'if':
            parsed = _IF_ARGS_RE.match(args)
            stack.append((
                ('if', bool(parsed and parsed.group(1)), parsed.group(2) if parsed else None),
                [],
            ))
        elif tag == 'for':
            parsed = _FOR_ARGS_RE.match(args)
            stack.append((
                ('for', parsed.group(1) if parsed else None, parsed.group(2) if parsed else None),
                [],
            ))
        elif len(stack) > 1:
            _close(stack)
        # endif/endfor sin bloque abierto: se descarta, no se imprime.

    if position < len(template):
        stack[-1][1].append(('text', template[position:]))
    while len(stack) > 1:  # bloques sin cerrar: se cierran al final
        _close(stack)
    return root


def _close(stack):
    meta, children = stack.pop()
    stack[-1][1].append(meta + (children,))


def _render_nodes(nodes, context):
    out = []
    for node in nodes:
        if node[0] == 'text':
            out.append(_render_vars(node[1], context))
        elif node[0] == 'if':
            _tag, negated, path, children = node
            truthy = bool(_lookup(context, path)) if path else False
            if truthy != negated:
                out.append(_render_nodes(children, context))
        else:
            _tag, item_var, path, children = node
            items = _lookup(context, path) if path else None
            if item_var and isinstance(items, (list, tuple)):
                for item in items:
                    out.append(_render_nodes(children, dict(context, **{item_var: item})))
    return ''.join(out)


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
    assert render('{% if not company.name %}no{% endif %}', ctx) == ''
    assert render('{% if empty %}no{% endif %}', ctx) == ''
    assert render('{% for i in items %}{{ i.n }}={{ i.v }};{% endfor %}', ctx) == 'Efectivo=10;Tarjeta=5;'
    assert render('{% for i in empty %}x{% endfor %}', ctx) == ''
    assert render('{% for i in nope %}x{% endfor %}', ctx) == ''
    assert render('{% if items %}{% for i in items %}{{ i.n }},{% endfor %}{% endif %}', ctx) == 'Efectivo,Tarjeta,'

    # ── Corte Z: rutas con punto en {% if %} y {% for %} ──────────────────
    z = {
        'cash_moves': [{'name': 'Retiro', 'amount': '-$50.00'}],
        'payments': [],
        'dte_summary': {
            'fc': {'count': 2, 'initial': 'DTE-01-A', 'final': 'DTE-01-B', 'total': '$17.90',
                   'documents': [{'number': 'DTE-01-A'}, {'number': 'DTE-01-B'}]},
            'ccf': {'count': 0, 'initial': '', 'final': '', 'total': '$0.00', 'documents': []},
        },
    }
    # variables simples, caso verdadero y falso
    assert render('{% if cash_moves %}MOV{% endif %}', z) == 'MOV'
    assert render('{% if payments %}PAGO{% endif %}', z) == ''
    assert render('{% if not payments %}SIN PAGOS{% endif %}', z) == 'SIN PAGOS'
    # rutas con punto, caso verdadero y falso
    assert render('{% if dte_summary.fc.count %}FC{% endif %}', z) == 'FC'
    assert render('{% if dte_summary.ccf.count %}CCF{% endif %}', z) == ''
    assert render('{% if dte_summary.fc.documents %}FCD{% endif %}', z) == 'FCD'
    assert render('{% if dte_summary.ccf.documents %}CCFD{% endif %}', z) == ''
    assert render('{% if dte_summary.nope.count %}X{% endif %}', z) == ''
    assert render('{{ dte_summary.ccf.count }}|{{ dte_summary.fc.total }}', z) == '0|$17.90'
    # if + for juntos
    assert render(
        '{% if dte_summary.fc.documents %}{% for doc in dte_summary.fc.documents %}'
        '[{{ doc.number }}]{% endfor %}{% endif %}', z
    ) == '[DTE-01-A][DTE-01-B]'
    assert render(
        '{% if dte_summary.ccf.documents %}{% for doc in dte_summary.ccf.documents %}'
        '[{{ doc.number }}]{% endfor %}{% endif %}', z
    ) == ''
    # if anidado dentro de if (el bug que imprimía los tags literalmente)
    assert render('{% if dte_summary.fc.documents %}X{% if dte_summary.fc.count %}Y'
                  '{% endif %}Z{% endif %}', z) == 'XYZ'
    assert render('{% if dte_summary.fc.documents %}X{% if dte_summary.ccf.count %}Y'
                  '{% endif %}Z{% endif %}', z) == 'XZ'
    assert render('{% if dte_summary.ccf.count %}X{% if dte_summary.fc.count %}Y'
                  '{% endif %}Z{% endif %}', z) == ''
    # if dentro de for, y for dentro de for
    assert render('{% for doc in dte_summary.fc.documents %}{% if doc.number %}'
                  '<{{ doc.number }}>{% endif %}{% endfor %}', z) == '<DTE-01-A><DTE-01-B>'
    assert render('{% for a in items %}{% for b in items %}{{ a.n }}/{{ b.n }};'
                  '{% endfor %}{% endfor %}', ctx) == (
        'Efectivo/Efectivo;Efectivo/Tarjeta;Tarjeta/Efectivo;Tarjeta/Tarjeta;')
    # tres niveles
    assert render('{% if dte_summary.fc.documents %}a{% if dte_summary.fc.count %}b'
                  '{% for d in dte_summary.fc.documents %}{{ d.number }}{% endfor %}'
                  'c{% endif %}d{% endif %}', z) == 'abDTE-01-ADTE-01-Bcd'

    # ── ningún tag se imprime literalmente, ni con plantillas rotas ───────
    rotas = [
        '{% if dte_summary.fc.count %}sin cierre',
        'huérfano {% endif %} suelto',
        '{% endfor %}{% if payments %}x{% endif %}',
        '{% if dte_summary.fc.count %}{% for d in dte_summary.fc.documents %}x{% endif %}',
        '{% if a and b %}raro{% endif %}',
        '{% for %}incompleto{% endfor %}',
    ]
    for rota in rotas:
        assert '{%' not in render(rota, z), rota

    print('template_renderer OK')
