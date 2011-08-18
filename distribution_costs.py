# -*- coding: utf-8 -*-
##############################################################################
#
#    distribution_costs module for OpenERP, Computes average purchase price from invoices and misc costs
#    Copyright (C) 2011 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Sylvain Garancher <sylvain.garancher@syleam.fr>
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
import time


class distribution_costs(osv.osv):
    _name = 'distribution.costs'
    _description = 'Distribution Costs'

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
        'name': fields.char('Case reference', size=64, required=True, help='Name of the case'),
        'date': fields.datetime('Date', help='Date of the case'),
        'origin': fields.char('External reference', size=64, required=True, help='Name of the origin document'),
        'description': fields.char('Label', size=64, required=True, help='Label of the case'),
        'partner_id': fields.many2one('res.partner', 'Shipping company', required=True, help='Partner name'),
        'address_id': fields.many2one('res.partner.address', 'From address', required=True, help='Partner address'),
        'weight': fields.float('Weight', help='Total weight'),
        'volume': fields.float('Volume', help='Total volume'),
        'weight_volume': fields.function(_compute_weight_volume, method=True, string='Weight volume', type='float', store=False, help='Weight/Volume value'),
        'state': fields.selection([('draft', 'Draft'), ('in_progress', 'In Progress'), ('confirmed', 'Confirmed'), ('updated', 'Updated'), ('done', 'Done'), ('canceled', 'Canceled')], 'State', required=True, readonly=True, help='State of the dstribution costs case',),
        'invoice_ids': fields.one2many('account.invoice', 'distribution_id', 'Invoices', help='List of costs invoices'),
        'line_ids': fields.one2many('distribution.costs.line', 'costs_id', 'Invoices list', help='Article lines details'),
        'company_id': fields.many2one('res.company', 'Company', help='Company of the distribution cost case'),
        'product_id': fields.related('line_ids', 'product_id', type='many2one', relation='product.product', string='Product', help='Products of the lines, used for search view'),
    }

    _defaults = {
        'name': lambda self, cr, uid, ids, c = None: self.pool.get('ir.sequence').get(cr, uid, 'distribution.costs'),
        'date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': 'draft',
    }

    def read_invoices(self, cr, uid, ids, context=None):
        """
        Read invoices to create distribution costs lines
        """
        distribution_costs_line_obj = self.pool.get('distribution.costs.line')
        account_invoice_line_obj = self.pool.get('account.invoice.line')
        product_template_obj = self.pool.get('product.template')

        # Retrieve fret invoice lines
        fret_invoice_line_ids = account_invoice_line_obj.search(cr, uid, [('invoice_id.distribution_id', 'in', ids), ('invoice_id.distribution', '=', True), ('product_id.categ_id.fret', '=', True)], context=context)
        # Compute total fret amount
        fret_amount = account_invoice_line_obj.read(cr, uid, fret_invoice_line_ids, ['price_subtotal'], context=context)
        fret_amount = sum([data['price_subtotal'] for data in fret_amount])

        # Retrieve product invoice lines
        product_invoice_line_ids = account_invoice_line_obj.search(cr, uid, [('invoice_id.distribution_id', 'in', ids), ('invoice_id.distribution', '=', False), ('product_id.categ_id.fret', '=', False)], context=context)
        # Compute total product amount
        product_amount = account_invoice_line_obj.read(cr, uid, product_invoice_line_ids, ['price_subtotal'], context=context)
        product_amount = sum([data['price_subtotal'] for data in product_amount])

        # Compute lines data
        data_list = []
        for invoice_line in account_invoice_line_obj.browse(cr, uid, product_invoice_line_ids, context=context):
            product_id = invoice_line.product_id

            # Retrieve intrastat_id, raise if not found
            intrastat_id = product_id.intrastat_id or product_id.categ_id and product_id.categ_id.intrastat_id
            if not intrastat_id:
                raise osv.except_osv(_('Error'), _('Intrastat code not found on product %s !' % product_id.name))

            # Retrieve taxes for this line from intrastat code
            tax_data = []
            for tax_id in intrastat_id.tax_ids:
                tax_data.append((0, 0, {'tax_id': tax_id.id}))

            data_list.append({
                'costs_id': invoice_line.invoice_id.distribution_id.id,
                'product_id': product_id.id,
                'fret': fret_amount * product_amount / invoice_line.quantity / invoice_line.price_subtotal,
                'quantity': invoice_line.quantity,
                'volume': product_id.volume,
                'weight': product_id.weight,
                'price_unit': invoice_line.price_unit,
                'tax_ids': tax_data,
                'company_id': invoice_line.invoice_id.distribution_id.company_id.id,
            })

        # Create lines
        for data in data_list:
            new_id = distribution_costs_line_obj.create(cr, uid, data, context=context)

    def compute_cost_price(self, cr, uid, ids, context=None):
        """
        This method does nothing in this module
        It must be inherited by other modules
        """
        raise NotImplementedError(_('The compute_cost_price method is not implemented on this object !'))

    def update_cost_price(self, cr, uid, ids, context=None):
        """
        This method updates products costs from lines
        """
        # TODO
        pass

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
        lines_data = self.read(cr, uid, ids, ['price_unit', 'fret'], context=context)

        res = {}
        for line_data in lines_data:
            id = line_data['id']
            res[id] = {}

            # Retrieve data from the tax lines
            distribution_costs_line_tax_ids = distribution_costs_line_tax_obj.search(cr, uid, [('line_id', '=', id)], context=context)
            tax_amounts = distribution_costs_line_tax_obj.read(cr, uid, distribution_costs_line_tax_ids, ['amount_tax'], context=context)

            # Computes total tax aount from tax lines
            res[id]['total_tax'] = sum([data['amount_tax'] for data in tax_amounts])

            # Computes cost price of the line
            res[id]['cost_price'] = line_data['price_unit'] + line_data['fret'] + res[id]['total_tax']

            # Computes coef of the line
            res[id]['coef'] = res[id]['cost_price'] / line_data['price_unit']

        return res

    _columns = {
        'costs_id': fields.many2one('distribution.costs', 'Distribution Costs', required=True, ondelete='cascade', help='Distribution Costs'),
        'product_id': fields.many2one('product.product', 'Product', readonly=True, required=True, help='Invoiced product'),
        'quantity': fields.float('Quantity', readonly=True, help='Total quantity of invoiced products'),
        'fret': fields.float('Fret', readonly=True, help='Amount of fret'),
        'weight': fields.float('Weight', readonly=True, help='Total weight, used for some costs'),
        'volume': fields.float('Volume', readonly=True, help='Total volume, used for some costs'),
        'price_unit': fields.float('Price unit', readonly=True, help='Price unit of the product'),
        'total_tax': fields.function(_compute_values, method=True, string='Tax amount', type='float', multi='prices', store=False, help='Total tax amount'),
        'cost_price': fields.function(_compute_values, method=True, string='Cost Price', type='float', multi='prices', store=False, help='Computed cost price'),
        'coef': fields.function(_compute_values, method=True, string='Coefficient', type='float', multi='prices', store=False, help='[Cost price / Unit price] coefficient'),
        'manual_coef': fields.float('Modified Coefficient', help='Coefficient modifier'),
        'tax_ids': fields.one2many('distribution.costs.line.tax', 'line_id', 'Taxes', readonly=True, help='Taxes use to compute cost price'),
        'company_id': fields.many2one('res.company', 'Company', readonly=True, help='Company of the line'),
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
            taxes_value = account_tax_obj.compute_all(cr, uid, [tax_line.tax_id], tax_line.base_amount, 1, address_id=costs_id.address_id.id, product=tax_line.line_id.product_id.id, partner=costs_id.partner_id.id)
            res[tax_line.id] = sum([data.get('amount', 0.) for data in taxes_value['taxes']])

        return res

    _columns = {
        'line_id': fields.many2one('distribution.costs.line', 'Product Line', help='Product line for this tax'),
        'tax_id': fields.many2one('account.tax', 'Tax', help='Tax applied on the amount'),
        'base_amount': fields.related('line_id', 'price_unit', type='float',string='Base Amount', help='Base amount used to compute the tax'),
        'amount_tax': fields.function(_compute_tax_amount, method=True, string='Tax Amount', type='float', store=False, help='Computed tax amount'),
        'company_id': fields.many2one('res.company', 'Company', help='Company of the line tax'),
    }

distribution_costs_line_tax()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
