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
import decimal_precision as dp


class stock_move(osv.osv):
    _inherit = 'stock.move'

    _columns = {
        'average_price': fields.float('Average Price', help='Average price on a purchase order'),
        'invoice_line_id': fields.many2one('account.invoice.line', 'Account invoice lines', ),
    }

stock_move()


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _invoice_line_hook(self, cr, uid, move_line, invoice_line_id):
        """
        Call after the creation of the invoice line
        We haven't link between invoice_line and move line if the invoice is create with picking
        """
        self.pool.get('stock.move').write(cr, uid, [move_line.id], {'invoice_line_id': invoice_line_id})
        return super(stock_picking, self)._invoice_line_hook(cr, uid, move_line, invoice_line_id)

stock_picking()

class stock_inventory_valuation(osv.osv):
    _name = 'stock.inventory.valuation'
    _description = 'Stock Inventory Valuation'
    _rec_name = 'product_id'
    _order = 'product_id'

    _columns = {
        'date': fields.date('Date of Inventory Valuation', help='Date of stock inventory valuation'),
        'product_id': fields.many2one('product.product', 'Product'),
        'qty': fields.float('Qty', digits_compute=dp.get_precision('Product UoM')),
        'uom_id': fields.many2one('product.uom', 'UoM', help='UoM by default'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'location_id': fields.many2one('stock.location', 'Location'),
        'standard_price': fields.float('Standard price', digits_compute=dp.get_precision('Purchase Price')),
        'cost_price': fields.float('Stock Valuation', digits_compute=dp.get_precision('Purchase Price'), help='Standard Price x Quantity'),
    }

stock_inventory_valuation()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
