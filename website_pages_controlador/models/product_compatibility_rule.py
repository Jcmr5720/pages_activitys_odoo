from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ProductCompatibilityRule(models.Model):
    _name = "product.compatibility.rule"
    _description = "Regla de compatibilidad entre categorías"

    name = fields.Char(string="Nombre", required=True)

    category_a_id = fields.Many2one("product.category", string="Categoría A", required=True)
    category_b_id = fields.Many2one("product.category", string="Categoría B")
    attribute_a_id = fields.Many2one("product.attribute", string="Atributo de compatibilidad Categoría 1", required=True)
    attribute_b_id = fields.Many2one("product.attribute", string="Atributo de compatibilidad Categoría 2")
    rule_type = fields.Selection(
        [
            ("single", "Regla simple"),
            ("multiple", "Múltiples categorías"),
        ],
        string="Tipo de regla",
        default="single",
        required=True,
    )
    operator = fields.Selection([
        ('=', 'Igual a'),
        ('<=', 'Menor o Igual (numérico)'),
        ('>=', 'Mayor o Igual (numérico)'),
        ('sequence_le', 'Menor o Igual (por prioridad)'),
        ('sequence_ge', 'Mayor o Igual (por prioridad)'),
        ('sum_gt', 'Mayor que (sumatoria)'),
        ('sum_lt', 'Menor que (sumatoria)')
    ], string="Operador")
    operator_single = fields.Selection(
        selection="_get_single_operator_selection",
        string="Operador",
        compute="_compute_operator_single",
        inverse="_inverse_operator_single",
        readonly=False,
    )
    rule_tip = fields.Char(string="Sugerencia")
    multi_category_line_ids = fields.One2many(
        "product.compatibility.rule.line",
        "rule_id",
        string="Categorías relacionadas",
    )
    multi_category_line_count = fields.Integer(
        string="Total de categorías relacionadas",
        compute="_compute_multi_category_line_count",
    )

    @api.constrains('operator', 'rule_type')
    def _check_operator_by_type(self):
        for rule in self:
            if rule.operator in {'sum_gt', 'sum_lt'} and rule.rule_type != 'multiple':
                raise ValidationError(
                    "El operador de sumatoria solo puede usarse con reglas de múltiples categorías."
                )
            if rule.rule_type == 'single' and (not rule.category_b_id or not rule.attribute_b_id):
                raise ValidationError(
                    "Las reglas simples requieren la categoría y atributo B definidos."
                )

    def check_compatibility(self, product1, product2, selected_products=None):
        """Evalúa si dos productos son compatibles según las reglas configuradas"""

        if not product1 or not product2:
            return False

        cat1, cat2 = product1.categ_id, product2.categ_id
        if not cat1 or not cat2:
            return False

        rules = self.search([
            "|",
            "&",
            ("category_a_id", "=", cat1.id),
            "|",
            ("category_b_id", "=", cat2.id),
            ("multi_category_line_ids.category_id", "=", cat2.id),
            "&",
            ("category_a_id", "=", cat2.id),
            "|",
            ("category_b_id", "=", cat1.id),
            ("multi_category_line_ids.category_id", "=", cat1.id),
        ])

        if not rules:
            return True

        selected_products = selected_products or self.env['product.product']

        for rule in rules:
            if rule.rule_type == 'multiple':
                if not rule._check_multiple_categories(product1, product2, selected_products):
                    return False
                continue
            # Según el sentido de la regla, intercambiar atributos
            if rule.category_a_id.id == cat1.id:
                attr_a, attr_b = rule.attribute_a_id, rule.attribute_b_id
                prod_a, prod_b = product1, product2
            else:
                attr_a, attr_b = rule.attribute_b_id, rule.attribute_a_id
                prod_a, prod_b = product2, product1

            val_a, val_a_num, order_a = rule._get_attribute_details(prod_a, attr_a)
            val_b, val_b_num, order_b = rule._get_attribute_details(prod_b, attr_b)

            if val_a is None or val_b is None:
                continue

            _logger.info(
                "Comparando atributos %s (%s) y %s (%s) con secuencias %s y %s",
                attr_a.display_name,
                val_a,
                attr_b.display_name,
                val_b,
                order_a,
                order_b,
            )

            is_number = val_a_num is not None and val_b_num is not None

            compatible = True
            if rule.operator == "=":
                compatible = (val_a == val_b)
            elif is_number and rule.operator == "<=":
                compatible = (val_a_num <= val_b_num)
            elif is_number and rule.operator == ">=":
                compatible = (val_a_num >= val_b_num)
            elif rule.operator == "sequence_le":
                compatible = (
                    order_a is not None
                    and order_b is not None
                    and order_b <= order_a
                )
            elif rule.operator == "sequence_ge":
                compatible = (
                    order_a is not None
                    and order_b is not None
                    and order_b >= order_a
                )

            if not compatible:
                return False

        return True

    def _get_attribute_details(self, product, attribute):
        if not product or not attribute:
            return (None, None, None)

        line = product.attribute_line_ids.filtered(lambda l: l.attribute_id == attribute)
        values = line.mapped("product_template_value_ids")
        if not values:
            return (None, None, None)

        value_record = values[0]
        value = getattr(value_record, "name", False) or str(value_record)

        numeric_value = None
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            numeric_value = None

        order = self._get_attribute_value_order(attribute, value_record)
        return (value, numeric_value, order)

    def _check_multiple_categories(self, product1, product2, selected_products):
        self.ensure_one()

        if not self.multi_category_line_ids:
            return True

        cat_a = self.category_a_id
        if product1.categ_id == cat_a:
            main_product = product1
            other_product = product2
        elif product2.categ_id == cat_a:
            main_product = product2
            other_product = product1
        else:
            return True

        line_categories = self.multi_category_line_ids.mapped("category_id")
        if other_product.categ_id not in line_categories:
            return True

        _, value_main_num, _ = self._get_attribute_details(main_product, self.attribute_a_id)
        if value_main_num is None:
            return True

        aggregated_products = (selected_products | product1 | product2)

        total = 0.0
        has_value = False
        for line in self.multi_category_line_ids:
            products_in_category = aggregated_products.filtered(lambda p: p.categ_id == line.category_id)
            for prod in products_in_category:
                _, numeric_value, _ = self._get_attribute_details(prod, line.attribute_id)
                if numeric_value is not None:
                    total += numeric_value
                    has_value = True

        if not has_value:
            return True

        if self.operator == "sum_gt":
            compatible = value_main_num > total
        elif self.operator == "sum_lt":
            compatible = value_main_num < total
        else:
            compatible = True

        return compatible

    def _compute_multi_category_line_count(self):
        for rule in self:
            rule.multi_category_line_count = len(rule.multi_category_line_ids)

    def action_open_multi_category_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Categorías relacionadas',
            'res_model': 'product.compatibility.rule.line',
            'view_mode': 'tree,form',
            'domain': [('rule_id', '=', self.id)],
            'context': {'default_rule_id': self.id},
            'target': 'current',
        }

    def _get_attribute_value_order(self, attribute, value_record):
        """Obtiene un valor numérico que represente el orden de un atributo."""
        if not attribute or not value_record:
            return None

        attribute_value = getattr(value_record, "product_attribute_value_id", False)
        if not attribute_value:
            attribute_value = getattr(value_record, "attribute_value_id", False)

        if attribute_value and hasattr(attribute_value, "sequence"):
            return attribute_value.sequence

        if hasattr(value_record, "sequence"):
            return value_record.sequence

        values = attribute.value_ids.sorted(key=lambda v: (v.sequence, v.id))
        for index, attr_value in enumerate(values):
            if attr_value.name == getattr(value_record, "name", None):
                return index

        return None

    @api.model
    def _get_single_operator_selection(self):
        return [
            ('=', 'Igual a'),
            ('<=', 'Menor o Igual (numérico)'),
            ('>=', 'Mayor o Igual (numérico)'),
            ('sequence_le', 'Menor o Igual (por prioridad)'),
            ('sequence_ge', 'Mayor o Igual (por prioridad)'),
        ]

    @api.depends('operator')
    def _compute_operator_single(self):
        allowed = {code for code, _ in self._get_single_operator_selection()}
        for rule in self:
            rule.operator_single = rule.operator if rule.operator in allowed else False

    def _inverse_operator_single(self):
        for rule in self:
            rule.operator = rule.operator_single


class ProductCompatibilityRuleLine(models.Model):
    _name = "product.compatibility.rule.line"
    _description = "Línea para reglas de compatibilidad múltiples"

    rule_id = fields.Many2one(
        "product.compatibility.rule",
        string="Regla",
        required=True,
        ondelete="cascade",
    )
    category_id = fields.Many2one(
        "product.category",
        string="Categoría",
        required=True,
    )
    attribute_id = fields.Many2one(
        "product.attribute",
        string="Atributo",
        required=True,
    )
