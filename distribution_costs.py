# -*- coding: utf-8 -*-
##############################################################################
#
#    distribution_costs module for OpenERP, Computes average purchase price from invoices and misc costs
#    Copyright (C) 2011 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Sylvain Garancher <sylvain.garancher@syleam.fr>
#              Sebastien LANGE <sebastien.lange@syleam.fr>
#
#    This file is a part of distribution_costs
#
#    distribution_costs is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    distribution_costs is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from osv import osv
from osv import fields
from tools.translate import _
import decimal_precision as dp
from datetime import datetime, timedelta
import tools


class distribution_costs(osv.osv):
    _name = 'distribution.costs'
    _description = 'Distribution Costs'
    _inherit = ['mail.thread']

    def _compute_weight_volume(self, cr, uid, ids, field_name, arg, context=None):
        """
        Computes the weight/volume value
        """
        res = {}
        for data in self.browse(cr, uid, ids, context=context):
            weight_volume_formula = data.company_id and data.company_id.weight_volume_formula or ''

            # Computes the value
            res[data.id] = 0.
            if weight_volume_formula:
                localdict = {'weight': data.weight, 'volume': data.volume}
                exec 'result = %s' % weight_volume_formula in localdict
                res[data.id] = localdict.get('result', 0.)

        return res

    _columns = {
        'name': fields.char('Case reference', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]}, help='Name of the case'),
        'date': fields.datetime('Date', readonly=True, states={'draft': [('readonly', False)]}, help='Date of the case'),
        'origin': fields.char('External reference', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]}, help='Name of the origin document'),
        'description': fields.char('Label', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]}, help='Label of the case'),
        'partner_id': fields.many2one('res.partner', 'Shipping company', required=True, readonly=True, states={'draft': [('readonly', False)]}, help='Partner name'),
        'address_id': fields.many2one('res.partner', 'From address', required=True, readonly=True, states={'draft': [('readonly', False)]}, help='Partner address'),
        'weight': fields.float('Weight', readonly=True, states={'draft': [('readonly', False)]}, help='Total weight'),
        'volume': fields.float('Volume', readonly=True, states={'draft': [('readonly', False)]}, help='Total volume'),
        'weight_volume': fields.function(_compute_weight_volume, method=True, string='Weight volume', type='float', store=False, help='Weight/Volume value'),
        'state': fields.selection([('draft', 'Draft'), ('in_progress', 'In Progress'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('canceled', 'Canceled')], 'State', required=True, readonly=True, help='State of the dstribution costs case',),
        'invoice_ids': fields.one2many('account.invoice', 'distribution_id', 'Invoices', readonly=True, states={'draft': [('readonly', False)]}, help='List of costs invoices'),
        'line_ids': fields.one2many('distribution.costs.line', 'costs_id', 'Invoices list', readonly=True, states={'in_progress': [('readonly', False)]}, help='Article lines details'),
        'company_id': fields.many2one('res.company', 'Company', readonly=True, help='Company of the distribution cost case'),
        'product_id': fields.related('line_ids', 'product_id', type='many2one', relation='product.product', string='Product', help='Products of the lines, used for search view'),
        'fret_amount': fields.float('Fret Amount', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft': [('readonly', False)]}, help="If we haven't invoice's fret, we can used this field"),
    }

    _defaults = {
        'name': lambda self, cr, uid, ids, c=None: self.pool.get('ir.sequence').get(cr, uid, 'distribution.costs'),
        # TODO : Find a better solution to get the datetime default value in user's timezone
        'date': lambda self, cr, uid, ids, c=None: fields.datetime.context_timestamp(cr, uid, timestamp=datetime.now(), context=c).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
        'state': 'draft',
        'company_id': lambda self, cr, uid, c=None: self.pool.get('res.company')._company_default_get(cr, uid, 'distribution.costs', context=c),
        'weight': 0.0,
        'volume': 0.0,
        'fret_amount': 0.0,
    }

    def _prepare_tax_data(self, cr, uid, invoice_line, tax_data, context=None):
        """
        Used for adding specific taxes
        """
        return tax_data

    def read_invoices(self, cr, uid, ids, context=None):
        """
        Read invoices to create distribution costs lines
        """
        distribution_costs_line_obj = self.pool.get('distribution.costs.line')
        account_invoice_line_obj = self.pool.get('account.invoice.line')
        res_currency_obj = self.pool.get('res.currency')
        distribution_costs = self.browse(cr, uid, ids[0], context=context)

        # Retrieve fret invoice lines
        fret_invoice_line_ids = account_invoice_line_obj.search(cr, uid, [
            ('invoice_id.state', 'not in', ('draft', 'cancel')),
            ('invoice_id.distribution_id', 'in', ids),
            ('invoice_id.distribution', '=', True),
            ('product_id.categ_id.fret', '=', True)
        ], context=context)
        # Compute total fret amount
        fret_amount = distribution_costs.fret_amount
        for line in account_invoice_line_obj.browse(cr, uid, fret_invoice_line_ids, context=context):
            fret_amount += res_currency_obj.compute(cr, uid, line.invoice_id.currency_id.id, distribution_costs.company_id.currency_id.id, line.price_subtotal)

        # Retrieve product invoice lines
        product_invoice_line_ids = account_invoice_line_obj.search(cr, uid, [
            ('invoice_id.state', 'not in', ('draft', 'cancel')),
            ('invoice_id.distribution_id', 'in', ids),
            ('invoice_id.distribution', '=', False),
            ('product_id.categ_id.fret', '=', False)
        ], context=context)
        # Compute total product amount
        product_amount = 0.
        for line in account_invoice_line_obj.browse(cr, uid, product_invoice_line_ids, context=context):
            product_amount += res_currency_obj.compute(cr, uid, line.invoice_id.currency_id.id, distribution_costs.company_id.currency_id.id, line.price_subtotal)

        # Compute lines data
        data_list = []
        for invoice_line in account_invoice_line_obj.browse(cr, uid, product_invoice_line_ids, context=context):
            product_id = invoice_line.product_id

            # Retrieve intrastat_id, raise if not found
            intrastat_id = product_id.intrastat_id or product_id.categ_id and product_id.categ_id.intrastat_id

            # Retrieve taxes for this line from intrastat code
            tax_data = []
            if intrastat_id:
                for tax_id in intrastat_id.tax_ids:
                    tax_data.append((0, 0, {'tax_id': tax_id.id}))
            tax_data = self._prepare_tax_data(cr, uid, invoice_line, tax_data, context=context)

            line_price_subtotal = res_currency_obj.compute(cr, uid, invoice_line.invoice_id.currency_id.id, distribution_costs.company_id.currency_id.id, invoice_line.price_subtotal)
            line_price_unit = res_currency_obj.compute(cr, uid, invoice_line.invoice_id.currency_id.id, distribution_costs.company_id.currency_id.id, invoice_line.price_unit)

            data_list.append({
                'costs_id': invoice_line.invoice_id.distribution_id.id,
                'product_id': product_id.id,
                'fret_total': fret_amount * line_price_subtotal / product_amount,
                'quantity': invoice_line.quantity,
                'volume': product_id.volume * invoice_line.quantity,
                'weight': product_id.weight * invoice_line.quantity,
                'price_total': line_price_unit * invoice_line.quantity,
                'tax_ids': tax_data,
                'invoice_line_id': invoice_line.id,
            })

        if data_list == []:
            raise osv.except_osv(_('Error'), _('No valid line found, please select valid invoices !'))

        # Create lines
        for data in data_list:
            distribution_costs_line_obj.create(cr, uid, data, context=context)

        return True

    def apply_cost(self, cr, uid, ids, distribution, line, move_ids, context=None):
        """
        Method to apply cost in move and product
        """
        if line.product_id.cost_method == 'std_distribution':
            line.product_id.write({'standard_price': line.cost_price_mod}, context=context)
        if line.product_id.cost_method == 'distribution' and move_ids:
            move_obj = self.pool.get('stock.move')
            product_obj = self.pool.get('product.product')
            product = line.product_id
            move = move_obj.browse(cr, uid, move_ids[0], context=context)
            ctx = dict(context, to_date=datetime.strftime(datetime.strptime(move.date, '%Y-%m-%d %H:%M:%S') + timedelta(seconds=-1), '%Y-%m-%d %H:%M:%S'))
            available_quantity = product_obj.browse(cr, uid, product.id, context=ctx).qty_available or 0
            # If no quantity available, standard price = unit price
            if available_quantity <= 0:
                new_standard_price = line.cost_price_mod
            # Else, compute the new standard price
            else:
                amount_unit = product.price_get('standard_price', context)[product.id]
                new_standard_price = ((amount_unit * available_quantity) + (line.cost_price_mod * move.product_qty)) / (available_quantity + move.product_qty)
            move_obj.write(cr, uid, move_ids, {'average_price': new_standard_price}, context=context)
            line.product_id.write({'standard_price': new_standard_price}, context=context)
        return True

    def update_cost_price(self, cr, uid, ids, context=None):
        """
        This method updates products costs from lines
        """
        purchase_line_obj = self.pool.get('purchase.order.line')
        stock_move_obj = self.pool.get('stock.move')

        for distribution_costs in self.browse(cr, uid, ids, context=context):
            for dc_line in distribution_costs.line_ids:
                # Update cost price on all moves linked to this line
                purchase_line_ids = purchase_line_obj.search(cr, uid, [
                    ('invoice_lines', 'in', dc_line.invoice_line_id.id),
                    ('product_id', '=', dc_line.product_id.id)
                ], context=context)
                stock_move_ids = stock_move_obj.search(cr, uid, [
                    ('invoice_line_id', '=', dc_line.invoice_line_id.id),
                    ('product_id', '=', dc_line.product_id.id)
                ], context=context)
                for line in purchase_line_obj.browse(cr, uid, purchase_line_ids, context=context):
                    stock_move_ids += [stock_move.id for stock_move in line.move_ids if line.product_id.id == dc_line.product_id.id]

                stock_move_ids = list(set(stock_move_ids))
                stock_move_obj.write(cr, uid, stock_move_ids, {'price_unit': dc_line.cost_price_mod, 'price_currency_id': distribution_costs.company_id.currency_id.id}, context=context)

                # Compute the new PUMP for products that are in "distribution" cost_method
                # If we have modified some moves, we have to compute the new PUMP for all "new" moves on this product
                self.apply_cost(cr, uid, ids, distribution_costs, dc_line, stock_move_ids, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        """
        Inherit copy method to avoid duplicating invoices when duplicating distribution costs case
        """
        default = {
            'invoice_ids': [],
            'line_ids': [],
        }
        return super(distribution_costs, self).copy(cr, uid, id, default, context=context)

distribution_costs()


class distribution_costs_line(osv.osv):
    _name = 'distribution.costs.line'
    _description = 'Distribution Costs Line'

    def _compute_values(self, cr, uid, ids, field_name, arg, context=None):
        """
        Computes the cost price
        """
        distribution_costs_line_tax_obj = self.pool.get('distribution.costs.line.tax')

        # Retrieve data from the line

        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            # Retrieve data from the tax lines
            distribution_costs_line_tax_ids = distribution_costs_line_tax_obj.search(cr, uid, [('line_id', '=', line.id)], context=context)

            # Computed values
            tax_total = sum(tax_line.amount_tax for tax_line in distribution_costs_line_tax_obj.browse(cr, uid, distribution_costs_line_tax_ids, context=context))
            price_unit = line.price_total / line.quantity
            fret_unit = line.fret_total / line.quantity
            tax_unit = tax_total / line.quantity
            cost_price = price_unit + fret_unit + tax_unit
            coef = cost_price / price_unit
            coef_mod = coef + line.manual_coef
            cost_price_mod = price_unit * coef_mod

            # Return values
            res[line.id] = {
                'tax_total': tax_total,
                'price_unit': price_unit,
                'fret_unit': fret_unit,
                'tax_unit': tax_unit,
                'cost_price': cost_price,
                'coef': coef,
                'cost_price_mod': cost_price_mod,
            }

        return res

    _columns = {
        'name': fields.char('Name', size=64, readonly=True, help='Name of the line'),
        'costs_id': fields.many2one('distribution.costs', 'Distribution Costs', required=True, ondelete='cascade', help='Distribution Costs'),
        'product_id': fields.many2one('product.product', 'Product', readonly=True, required=True, help='Invoiced product'),
        'quantity': fields.float('Quantity', readonly=True, help='Total quantity of invoiced products'),
        'weight': fields.float('Weight', help='Total weight, used for some costs'),
        'volume': fields.float('Volume', help='Total volume, used for some costs'),
        'tax_ids': fields.one2many('distribution.costs.line.tax', 'line_id', 'Taxes', readonly=True, help='Taxes use to compute cost price'),
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice line', readonly=True, help='Original invoice line for this distribution costs line'),
        'company_id': fields.many2one('res.company', 'Company', readonly=True, help='Company of the line'),

        'price_total': fields.float('Price total', readonly=True, digits_compute=dp.get_precision('Account'), help='Total price of the products'),
        'fret_total': fields.float('Fret', readonly=True, digits_compute=dp.get_precision('Account'), help='Amount of fret'),
        'tax_total': fields.function(_compute_values, method=True, string='Tax amount', type='float', digits_compute=dp.get_precision('Account'), multi='prices', store=True, help='Total tax amount'),

        'fret_unit': fields.function(_compute_values, method=True, string='Fret', type='float', digits_compute=dp.get_precision('Account'), multi='prices', store=True, help='Amount of fret'),
        'price_unit': fields.function(_compute_values, method=True, string='Price unit', type='float', digits_compute=dp.get_precision('Account'), multi='prices', store=True, help='Unit price of the product'),
        'tax_unit': fields.function(_compute_values, method=True, string='Tax amount', type='float', digits_compute=dp.get_precision('Account'), multi='prices', store=True, help='Total tax amount'),
        'coef': fields.function(_compute_values, method=True, string='Coefficient', type='float', multi='prices', store=True, help='[Cost price / Unit price] coefficient'),
        'cost_price': fields.function(_compute_values, method=True, string='Cost Price', type='float', digits_compute=dp.get_precision('Account'), multi='prices', store=True, help='Computed cost price'),
        'manual_coef': fields.float('Modified Coefficient', help='Coefficient modifier'),
        'cost_price_mod': fields.function(_compute_values, method=True, string='Modified Cost Price', type='float', digits_compute=dp.get_precision('Account'), multi='prices', store=True, help='Computed cost price, with manual_coef'),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c=None: self.pool.get('res.company')._company_default_get(cr, uid, 'distribution.costs', context=c),
        'weight': 0.0,
        'volume': 0.0,
        'price_total': 0.0,
        'fret_total': 0.0,
        'quantity': 0.0,
        'manual_coef': 0.0,
    }

distribution_costs_line()


class distribution_costs_line_tax(osv.osv):
    _name = 'distribution.costs.line.tax'
    _description = 'Distribution Costs Line Tax'

    def _compute_tax_amount(self, cr, uid, ids, field_name, arg, context=None):
        """
        Computes tax amount from base amount
        """
        account_tax_obj = self.pool.get('account.tax')
        res = {}

        for tax_line in self.browse(cr, uid, ids, context=context):
            costs_id = tax_line.line_id.costs_id

            base_value = tax_line.line_id.price_total
            if tax_line.tax_id.domain:
                base_value = getattr(tax_line.line_id, tax_line.tax_id.domain)

            # 1 as quantity because base_value includes the quantity
            taxes_value = account_tax_obj.compute_all(cr, uid, [tax_line.tax_id], base_value, 1, address_id=costs_id.address_id.id, product=tax_line.line_id.product_id.id, partner=costs_id.partner_id.id)
            res[tax_line.id] = sum([data.get('amount', 0.) for data in taxes_value['taxes']])

        return res

    _columns = {
        'name': fields.char('Name', size=64, readonly=True, help='Name of the line'),
        'line_id': fields.many2one('distribution.costs.line', 'Product Line', required=True, ondelete='cascade', help='Product line for this tax'),
        'tax_id': fields.many2one('account.tax', 'Tax', required=True, help='Tax applied on the amount'),
        'amount_tax': fields.function(_compute_tax_amount, method=True, string='Tax Amount', type='float', digits_compute=dp.get_precision('Account'), store=False, help='Computed tax amount'),
        'company_id': fields.many2one('res.company', 'Company', readonly=True, help='Company of the line tax'),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c=None: self.pool.get('res.company')._company_default_get(cr, uid, 'distribution.costs', context=c),
    }

distribution_costs_line_tax()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
