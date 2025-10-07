from odoo import models, fields


class WebsitePage(models.Model):
    """Simple model to manage website pages from the backend."""
    _name = 'website.custom.page'
    _description = 'Website Page'

    name = fields.Char(string='Name', required=True)
    url = fields.Char(string='URL')
