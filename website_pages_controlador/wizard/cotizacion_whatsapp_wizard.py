from urllib.parse import quote

from odoo import models, fields
from odoo.exceptions import UserError


class CotizacionWhatsAppWizard(models.TransientModel):
    _name = 'cotizacion.whatsapp.wizard'
    _description = 'Wizard to send WhatsApp messages for cotizaciones'

    cotizacion_id = fields.Many2one('website.constructor.cotizacion', required=True)
    ajuste_id = fields.Many2one(
        'website.constructor.ajuste',
        string='Mensaje',
        required=True,
        domain=[('activo', '=', True)],
    )

    def action_send(self):
        self.ensure_one()
        cotizacion = self.cotizacion_id
        if not cotizacion.telefono:
            raise UserError('El cliente no tiene un número de teléfono.')
        message = self.ajuste_id.obtener_mensaje({'cotizacion': cotizacion})
        url = 'https://wa.me/%s?text=%s' % (cotizacion.telefono, quote(message))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
