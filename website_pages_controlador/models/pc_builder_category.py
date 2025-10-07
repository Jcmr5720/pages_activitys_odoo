from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PcBuilderCategory(models.Model):
    _name = 'website.constructor.categoria'
    _description = 'Website Constructor Category'
    _order = 'secuencia, id'

    categoria_producto_id = fields.Many2one('product.category', string='Categoría de Producto', required=True)
    requerido = fields.Boolean(string='Requerido', default=False)
    elemento_menu_id = fields.Many2one(
        'website.constructor.menu',
        string='Elemento de Menú',
        required=True,
        ondelete='restrict',
    )
    mostrar_en_constructor = fields.Boolean(string='Mostrar en Constructor', default=True)
    requerimiento_inicial = fields.Boolean(string='Requerimiento Inicial', default=False)
    secuencia = fields.Integer(string='Secuencia', default=10)
    nombre = fields.Char(related='categoria_producto_id.name', store=True, readonly=True)

    @api.onchange('requerimiento_inicial')
    def _onchange_requerimiento_inicial(self):
        if self.requerimiento_inicial:
            self.requerido = True
            self.mostrar_en_constructor = True

    @api.model
    def create(self, vals):
        if vals.get('requerimiento_inicial'):
            if self.search_count([('requerimiento_inicial', '=', True)]):
                raise ValidationError('Solo puede existir una categoría con requerimiento inicial.')
            vals['requerido'] = True
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
                raise ValidationError('Solo puede existir una categoría con requerimiento inicial.')
            vals['requerido'] = True
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
                if 'requerido' in vals and not vals['requerido']:
                    raise ValidationError('Un elemento con requerimiento inicial debe ser requerido.')
                if 'mostrar_en_constructor' in vals and not vals['mostrar_en_constructor']:
                    raise ValidationError(
                        'Un elemento con requerimiento inicial debe mostrarse en el constructor.'
                    )
        return super().write(vals)
