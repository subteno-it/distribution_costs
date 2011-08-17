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


class product_category(osv.osv):
    _inherit = 'product.category'

    _columns = {
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat Code', help='Intrastat Code applied on the category'),
    }

product_category()


class product_template(osv.osv):
    _inherit = 'product.template'

    _columns = {
        'cost_method': fields.selection([('standard', 'Standard Price'), ('average', 'Average Price'), ('distribution', 'Average Price (Distribution)')], 'Costing Method', required=True,
            help="Standard Price: the cost price is fixed and recomputed periodically (usually at the end of the year), Average Price: the cost price is recomputed at each reception of products."),
    }

    def get_intrastat_id(self, cr, uid, ids, context=None):
        """
        Retrieve the intrastat id of the product template
        """
        # Retrieve products which have a defined intrastat_id
        in_template_ids = self.search(cr, uid, [('id','in', ids), ('intrastat_id', '!=', False)], context=context)
        not_in_template_ids = [val for val in ids if val not in in_template_ids]

        # If some products do not have intrastat_id, search on categories
        if not_in_template_ids:
            in_category_ids = self.search(cr, uid, [('id','in', ids), ('categ_id.intrastat_id', '!=', False)], context=context)
            not_in_category_ids = [val for val in not_in_template_ids if val not in in_category_ids]

            # If some products do not hav intrastat yet, raise
            raise osv.except_osv(_('Error'), _('Some products do not have intrastat code !'))

        res = {}

        # Retrieve intrastat_id on products
        if in_template_ids:
            for value in self.read(cr, uid, ids, ['intrastat_id'], context=context):
                res[value['id'][0]] = value['intrastat_id'][0]

        # Retrieve intrastat_id on categories
        if in_category_ids:
            product_category_obj = self.pool.get('product.category')
            categ_ids = self.read(cr, uid, ids, ['categ_id'], context=context)
            for value in self.read(cr, uid, [data['categ_id'][0] for data in categ_ids], ['intrastat_id'], context=context):
                res[value['id'][0]] = value['intrastat_id'][0]

        return res

product_template()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
