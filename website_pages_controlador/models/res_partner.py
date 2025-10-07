from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        cotizacion_id = self.env.context.get('cotizacion_id')
        if cotizacion_id:
            cotizacion = self.env['website.constructor.cotizacion'].browse(cotizacion_id)
            for partner in partners:
                cotizacion.write({
                    'partner_id': partner.id,
                    'usuario': partner.name,
                })
        return partners
