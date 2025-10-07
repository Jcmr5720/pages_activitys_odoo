from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website
import logging
import json
import re

_logger = logging.getLogger(__name__)


class WebsitePagesConstructor(Website):

    @http.route('/123', type='http', auth='public', website=True, sitemap=False)
    def pages(self, **kw):
        return request.render('website_pages_constructor.templates_constructor')

    @http.route('/pc_builder', type='http', auth='public', website=True, sitemap=False)
    def pc_builder(self, **kw):
        MenuItem = request.env['website.constructor.menu'].sudo()
        menu_items = MenuItem.search([('mostrar_en_constructor', '=', True)], order='secuencia, id')
        Category = request.env['website.constructor.categoria'].sudo()
        categories = Category.search(
            [
                ('mostrar_en_constructor', '=', True),
                ('elemento_menu_id', 'in', menu_items.ids),
            ],
            order='secuencia, id',
        )

        categories_data = [
            {
                'id': c.categoria_producto_id.id,
                'name': c.categoria_producto_id.name,
                'required': c.requerido,
                'group': c.elemento_menu_id.key,
                'initial': c.requerimiento_inicial,
            }
            for c in categories
        ]
        menu_items_data = [
            {'id': m.key, 'name': m.nombre, 'initial': m.requerimiento_inicial}
            for m in menu_items
        ]
        return request.render(
            'website_pages_constructor.templates_constructor',
            {
                'categories': categories_data,
                'menu_items': menu_items_data,
                'is_public': request.env.user._is_public(),
            },
        )

    @http.route(
        '/pc_builder/search',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=False,
    )
    def pc_builder_search(self, **kwargs):
        category_id = int(kwargs.get('category_id', 0))
        query = kwargs.get('query', '')
        domain = [('categ_id', '=', category_id)]
        if query:
            domain.append(('name', 'ilike', query))
        Product = request.env['product.product'].sudo()
        in_stock_domain = domain + [('qty_available', '>', 0)]
        out_of_stock_domain = domain + [('qty_available', '<=', 0)]

        in_stock_products = Product.search(
            in_stock_domain,
            order='qty_available desc, name',
        )
        out_of_stock_products = Product.search(
            out_of_stock_domain,
            order='qty_available desc, name',
        )

        products = in_stock_products | out_of_stock_products
        result = [
            {
                'id': p.id,
                'name': p.name,
                'price': p.list_price,
                'stock': p.qty_available,
                'image_url': f"/web/image/product.product/{p.id}/image_512",
            }
            for p in products
        ]
        return http.Response(
            json.dumps(result),
            content_type='application/json',
        )

    @http.route(
        '/pc_builder/add_to_cart',
        type='json',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=False,
    )
    def pc_builder_add_to_cart(self, product_ids=None, **kwargs):
        order = request.website.sale_get_order(force_create=1)
        for pid in product_ids or []:
            product = request.env['product.product'].sudo().browse(int(pid))
            if product.exists():
                order._cart_update(product_id=product.id, add_qty=1)
        return {'result': True}

    @http.route(
        '/pc_builder/check_compatibility',
        type='json',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=False,
    )
    def pc_builder_check_compatibility(self, product_id=None, selected_ids=None, **kwargs):
        Product = request.env['product.product'].sudo()
        product = Product.browse(int(product_id))
        selected_ids = [int(sid) for sid in (selected_ids or []) if sid]
        selected_products = Product.browse(selected_ids)
        rule_model = request.env['product.compatibility.rule'].sudo()

        selected_with_candidate = selected_products | product

        for sid in selected_ids:
            other = Product.browse(int(sid))
            if not rule_model.check_compatibility(product, other, selected_products=selected_with_candidate):
                msg = f"{product.name} no es compatible con {other.name}"
                return {'compatible': False, 'message': msg}

        return {'compatible': True, 'message': ''}

    @http.route(
        '/pc_builder/filter_compatibility',
        type='json',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=False,
    )
    def pc_builder_filter_compatibility(self, product_ids=None, selected_ids=None, **kwargs):
        product_ids = [int(pid) for pid in (product_ids or []) if pid]
        selected_ids = [int(sid) for sid in (selected_ids or []) if sid]

        Product = request.env['product.product'].sudo()
        products = Product.browse(product_ids)
        selected_products = Product.browse(selected_ids)
        rule_model = request.env['product.compatibility.rule'].sudo()

        compatibility = {pid: True for pid in product_ids}
        has_rules = False
        rule_cache = {}

        def _categories_key(cat_a, cat_b):
            if not cat_a or not cat_b:
                return None
            return tuple(sorted([cat_a.id, cat_b.id]))

        for product in products:
            if not product.exists():
                continue
            product_cat = product.categ_id
            for other in selected_products:
                if not other.exists() or other.id == product.id:
                    continue
                other_cat = other.categ_id
                key = _categories_key(product_cat, other_cat)
                if not key:
                    continue
                if key not in rule_cache:
                    rule_cache[key] = bool(
                        rule_model.search_count(
                            [
                                '|',
                                '&',
                                ('category_a_id', '=', key[0]),
                                ('category_b_id', '=', key[1]),
                                '&',
                                ('category_a_id', '=', key[1]),
                                ('category_b_id', '=', key[0]),
                            ],
                            limit=1,
                        )
                    )
                if not rule_cache[key]:
                    continue
                has_rules = True
                if not rule_model.check_compatibility(
                    product,
                    other,
                    selected_products=selected_products | product,
                ):
                    compatibility[product.id] = False
                    break

        return {'compatibility': compatibility, 'has_rules': has_rules}

    @http.route(
        '/pc_builder/quote',
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def pc_builder_quote(self, product_ids='', **kwargs):
        name = kwargs.get('name')
        phone = kwargs.get('phone')
        if isinstance(product_ids, str):
            product_ids = [int(pid) for pid in product_ids.split(',') if pid]
        if not product_ids:
            return request.redirect('/pc_builder')

        if request.env.user._is_public():
            if not name or not phone or not re.match(r'^\+\d+', phone):
                return request.redirect('/pc_builder')
        else:
            name = request.env.user.name
            phone = request.env.user.phone or ''

        partner = request.env.user.partner_id or request.website.partner_id
        order = request.env['sale.order'].sudo().create({'partner_id': partner.id})
        Product = request.env['product.product'].sudo()
        valid_product_ids = []
        for pid in product_ids:
            product = Product.browse(int(pid))
            if product.exists():
                valid_product_ids.append(product.id)
                is_out_of_stock = product.qty_available <= 0
                line_name = product.name
                price_unit = product.list_price
                if is_out_of_stock:
                    price_unit = 0.0
                    line_name = f"{product.name} (Bajo pedido)"
                request.env['sale.order.line'].sudo().create({
                    'order_id': order.id,
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': price_unit,
                    'name': line_name,
                })

        request.env['website.constructor.cotizacion'].sudo().create({
            'usuario': name,
            'telefono': phone,
            'producto_ids': [(6, 0, valid_product_ids)],
            'is_public': request.env.user._is_public(),
            'partner_id': request.env.user.partner_id.id if not request.env.user._is_public() else False,
        })
        pdf, _ = (
            request.env['ir.actions.report']
            .sudo()
            ._render_qweb_pdf('sale.report_saleorder', [order.id])
        )
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename="cotizacion.pdf"'),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

