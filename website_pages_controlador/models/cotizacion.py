from odoo import models, fields, api
from odoo.exceptions import UserError


class WebsiteConstructorCotizacion(models.Model):
    _name = 'website.constructor.cotizacion'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Cotización generada en el constructor de PC'

    usuario = fields.Char(string='Usuario', required=True)
    telefono = fields.Char(string='Teléfono')
    producto_ids = fields.Many2many('product.product', string='Productos')
    productos_sin_stock_ids = fields.Many2many(
        'product.product',
        string='Productos sin stock',
        compute='_compute_productos_sin_stock_ids',
    )
    total = fields.Float(string='Total', compute='_compute_total', store=True)
    fecha = fields.Datetime(string='Fecha', default=fields.Datetime.now, readonly=True)
    assigned_user_id = fields.Many2one('res.users', string='Asignado a', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    is_public = fields.Boolean(string='Usuario público', default=False)
    state = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('asignado', 'Asignado'),
    ], string='Estado', default='pendiente')
    sale_order_id = fields.Many2one('sale.order', string='Pedido de Venta', readonly=True)
    message_main_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Main Attachment',
        compute='_compute_message_main_attachment_id',
        inverse='_inverse_message_main_attachment_id',
        index=True,
    )

    def _compute_message_main_attachment_id(self):
        """Delegate computation to ``mail.thread`` implementation."""
        super()._compute_message_main_attachment_id()

    def _inverse_message_main_attachment_id(self):
        """Delegate inverse handling to ``mail.thread`` implementation."""
        super()._inverse_message_main_attachment_id()

    @api.depends('producto_ids')
    def _compute_total(self):
        for record in self:
            record.total = sum(record.producto_ids.mapped('list_price'))

    @api.depends('producto_ids', 'producto_ids.qty_available')
    def _compute_productos_sin_stock_ids(self):
        for record in self:
            record.productos_sin_stock_ids = record.producto_ids.filtered(
                lambda product: product.qty_available <= 0
            )

    def action_open_whatsapp_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cotizacion.whatsapp.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cotizacion_id': self.id,
            }
        }

    def action_open_assign_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cotizacion.assign.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('website_pages_controlador.view_cotizacion_assign_wizard_form').id,
            'target': 'new',
            'context': {
                'default_cotizacion_id': self.id,
            }
        }

    def action_open_create_client(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': self.usuario,
                'default_phone': self.telefono,
                'cotizacion_id': self.id,
            }
        }

    def action_open_assign_client_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cotizacion.assign.client.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cotizacion_id': self.id,
            }
        }

    def action_open_client_form(self):
        self.ensure_one()
        if not self.partner_id:
            return False

        action = self.env.ref('base.action_partner_form').read()[0]
        action.update({
            'res_id': self.partner_id.id,
            'views': [
                (self.env.ref('base.view_partner_form').id, 'form'),
            ],
        })
        return action

    def action_process_sale_order(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError('Debe asignar un cliente antes de procesar la cotización.')
        if not self.assigned_user_id:
            raise UserError('Debe asignar un vendedor antes de procesar la cotización.')

        order_lines = [(0, 0, {
            'product_id': product.id,
            'name': product.name,
            'product_uom_qty': 1,
            'price_unit': product.list_price,
        }) for product in self.producto_ids]

        sale_order_vals = {
            'partner_id': self.partner_id.id,
            'order_line': order_lines,
        }
        if self.assigned_user_id:
            sale_order_vals['user_id'] = self.assigned_user_id.id

        sale_order = self.env['sale.order'].create(sale_order_vals)
        self.sale_order_id = sale_order.id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
        }
