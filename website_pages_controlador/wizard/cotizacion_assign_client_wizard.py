from odoo import models, fields


class CotizacionAssignClientWizard(models.TransientModel):
    _name = 'cotizacion.assign.client.wizard'
    _description = 'Wizard to assign a client to quotation'

    cotizacion_id = fields.Many2one('website.constructor.cotizacion', required=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)

    def action_assign_client(self):
        self.ensure_one()
        self.cotizacion_id.write({
            'partner_id': self.partner_id.id,
            'usuario': self.partner_id.name,
        })
        return {'type': 'ir.actions.act_window_close'}
