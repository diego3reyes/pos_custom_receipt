from odoo import http
from odoo.http import request


class PosCorteZController(http.Controller):

    @http.route('/pos_custom_receipt/corte_z/<int:session_id>', type='http', auth='user')
    def corte_z(self, session_id, **kwargs):
        # search() aplica reglas de registro: si el usuario no puede ver la
        # sesión, simplemente no existe para él.
        session = request.env['pos.session'].search([('id', '=', session_id)], limit=1)
        if not session:
            return request.not_found()
        return request.make_response(
            session.get_corte_z_page(),
            headers=[('Content-Type', 'text/html; charset=utf-8')],
        )
