from odoo import models, fields
from odoo.tools.safe_eval import safe_eval


class WebsiteConstructorAjuste(models.Model):
    _name = "website.constructor.ajuste"
    _description = "Ajustes del constructor del sitio web"
    _rec_name = "nombre"

    nombre = fields.Char(string="Nombre")
    mensaje_predeterminado = fields.Text(string="Mensaje predeterminado")
    activo = fields.Boolean(string="Activo", default=True)
    ultima_modificacion = fields.Datetime(string="Última modificación", default=fields.Datetime.now)

    def obtener_mensaje(self, variables=None):
        """Renderiza el mensaje predeterminado con soporte para expresiones de Python."""
        self.ensure_one()
        variables = variables or {}
        localdict = {"env": self.env, "record": self}
        localdict.update(variables)
        try:
            return safe_eval(f"f'''{self.mensaje_predeterminado or ''}'''", localdict)
        except Exception:
            return self.mensaje_predeterminado
