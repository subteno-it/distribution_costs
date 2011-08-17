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
        'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('updated', 'Updated'), ('done', 'Done'), ('canceled', 'Canceled')], 'State', required=True, readonly=True, help='State of the dstribution costs case',),
        'goods_ids': fields.one2many('account.invoice', 'distribution_id', 'Invoice goods', domain=[('distribution_id','=','False')], help='List of goods invoices'),
        'costs_ids': fields.one2many('account.invoice', 'distribution_id', 'Invoice costs', domain=[('distribution_id','=','False')], help='List of costs invoices'),
        'line_ids': fields.one2many('distribution.costs.line', 'costs_id', 'Invoices list', help='Article lines details'),
        'company_id': fields.many2one('res.company', 'Company', help='Company of the distribution cost case'),
    }

    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': 'draft',
    }

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

    def _compute_total_tax(self, cr, uid, ids, field_name, arg, context=None):
        """
        Computes the sum of tax amounts in lines
        """
        distribution_costs_line_tax_obj = self.pool.get('distribution.costs.line.tax')

        res = {}
        for id in ids:
            # Computes total tax aount from tax lines
            distribution_costs_line_tax_ids = distribution_costs_line_tax_obj.search(cr, uid, [('line_id', '=', id)], context=context)
            tax_amounts = distribution_costs_line_tax_obj.read(cr, uid, distribution_costs_line_tax_ids, ['amount_tax'], context=context)
            res[id] = sum([data['amount_tax'] for data in tax_amounts])

        return res

    _columns = {
        'costs_id': fields.many2one('distribution.costs', 'Distribution Costs', required=True, help='Distribution Costs'),
        'product_id': fields.many2one('product.product', 'Product', required=True, help='Invoiced product'),
        'quantity': fields.float('Quantity', help='Total quantity of invoiced products'),
        'weight': fields.float('Weight', help='Total weight, used for some costs'),
        'volume': fields.float('Volume', help='Total volume, used for some costs'),
        'price_unit': fields.float('Price unit', help='Price unit of the product'),
        'cost_price': fields.float('Cost Price', readonly=True, help='Computed cost price, readonly'),
        'manual_cost_price': fields.float('Modified Cost Price', help='Modified cost price, saved on the product when validated'),
        'total_tax': fields.function(_compute_total_tax, method=True, string='Tax amount', type='float', store=False, help='Total tax amount'),
        'coef': fields.float('Coefficient', help='[Buy price / Cost price] coefficient'),
        'tax_ids': fields.one2many('distribution.costs.line.tax', 'line_id', 'Taxes', help='Taxes use to compute cost price'),
        'company_id': fields.many2one('res.company', 'Company', help='Company of the line'),
    }

    _defaults = {
        'manual_cost_price': lambda self, cr, uid, ids, c=None: self.browse(cr, uid, ids, context=c).cost_price,
    }

distribution_costs_line()


class distribution_costs_line_tax(osv.osv):
    _name = 'distribution.costs.line.tax'
    _description = 'Distribution Costs Line Tax'

    _columns = {
        'line_id': fields.many2one('distribution.costs.line', 'Product Line', help='Product line for this tax'),
        'tax_id': fields.many2one('account.tax', 'Tax', help='Tax applied on the amount'),
        'base_amount': fields.float('Base Amount', help='Base amount used to compute the tax'),
        'amount_tax': fields.float('Tax Amount', help='Computed tax amount'),
        'company_id': fields.many2one('res.company', 'Company', help='Company of the line tax'),
    }

distribution_costs_line_tax()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
