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


class stock_move(osv.osv):
    _inherit = 'stock.move'

    _columns = {
        'last_purchase_price': fields.float('Last Purchase Price', help='Last cost price on a purchase order'),
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
