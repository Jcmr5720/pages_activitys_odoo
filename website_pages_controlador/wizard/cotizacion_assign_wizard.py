from odoo import models, fields


class CotizacionAssignWizard(models.TransientModel):
    _name = 'cotizacion.assign.wizard'
    _description = 'Wizard to assign cotizacion to an internal user'

    cotizacion_id = fields.Many2one('website.constructor.cotizacion', required=True)
    user_id = fields.Many2one('res.users', string='Trabajador', required=True, domain=[('share', '=', False)])

    def action_assign(self):
        self.ensure_one()
        cotizacion = self.cotizacion_id
        cotizacion.write({
            'assigned_user_id': self.user_id.id,
            'state': 'asignado',
        })
        model_id = self.env['ir.model']._get('website.constructor.cotizacion').id
        activity_type = self.env.ref('mail.mail_activity_data_todo').id
        self.env['mail.activity'].create({
            'activity_type_id': activity_type,
            'res_id': cotizacion.id,
            'res_model_id': model_id,
            'user_id': self.user_id.id,
            'summary': f'Atender cotización {cotizacion.id}',
        })
        return {'type': 'ir.actions.act_window_close'}
