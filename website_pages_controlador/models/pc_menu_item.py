from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PcMenuItem(models.Model):
    _name = 'website.constructor.menu'
    _description = 'Website Constructor Menu'
    _order = 'secuencia, id'
    _rec_name = 'nombre'

    nombre = fields.Char(string='Nombre', required=True)
    key = fields.Char(string='Key', required=True)
    secuencia = fields.Integer(string='Secuencia', default=10)
    mostrar_en_constructor = fields.Boolean(string='Mostrar en Constructor', default=True)
    requerimiento_inicial = fields.Boolean(string='Requerimiento Inicial', default=False)
    categoria_ids = fields.One2many('website.constructor.categoria', 'elemento_menu_id', string='Categorías')

    def name_get(self):
        return [(record.id, record.nombre) for record in self]

    @api.onchange('requerimiento_inicial')
    def _onchange_requerimiento_inicial(self):
        if self.requerimiento_inicial:
            self.mostrar_en_constructor = True

    @api.model
    def create(self, vals):
        if vals.get('requerimiento_inicial'):
            if self.search_count([('requerimiento_inicial', '=', True)]):
                raise ValidationError('Solo puede existir un menú con requerimiento inicial.')
            vals['mostrar_en_constructor'] = True
            min_seq = self.search([], order='secuencia', limit=1)
            vals['secuencia'] = (min_seq.secuencia - 1) if min_seq else 0
        return super().create(vals)

    def write(self, vals):
        if vals.get('requerimiento_inicial'):
            existing = self.search([
                ('requerimiento_inicial', '=', True),
                ('id', 'not in', self.ids),
            ], limit=1)
            if existing:
                raise ValidationError('Solo puede existir un menú con requerimiento inicial.')
            vals['mostrar_en_constructor'] = True
            min_seq = self.search([('id', 'not in', self.ids)], order='secuencia', limit=1)
            vals['secuencia'] = (min_seq.secuencia - 1) if min_seq else 0
        elif 'requerimiento_inicial' not in vals and self.filtered('requerimiento_inicial'):
            min_seq = self.search([('id', 'not in', self.ids)], order='secuencia', limit=1)
            vals['secuencia'] = (min_seq.secuencia - 1) if min_seq else 0
        for rec in self:
            if rec.requerimiento_inicial and (
                'requerimiento_inicial' not in vals or vals['requerimiento_inicial']
            ):
                if 'mostrar_en_constructor' in vals and not vals['mostrar_en_constructor']:
                    raise ValidationError(
                        'Un elemento con requerimiento inicial debe mostrarse en el constructor.'
                    )
        return super().write(vals)

    def unlink(self):
        for menu in self:
            if menu.categoria_ids:
                raise ValidationError(
                    'No se puede eliminar el menú "%s" porque tiene categorías asociadas.'
                    % menu.display_name
                )
        return super().unlink()
