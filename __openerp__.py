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
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    distribution_costs is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Distribution Costs',
    'version': '1.2',
    'category': 'Generic Modules/Sales & Purchases',
    'description': """Computes average purchase price from invoices and misc costs

Use l10n_fr_intrastat_product module from Akretion.
This module replace report_intrastat and it's available to lp:new-report-intrastat.""",
    'author': 'SYLEAM',
    'website': 'http://www.syleam.fr/',
    'depends': [
        'base',
        'account',
        'product',
        'purchase',
        'stock',
        'l10n_fr_intrastat_product',
    ],
    'init_xml': [],
    'images': [],
    'update_xml': [
        'security/ir.model.access.csv',
        #'wizard/wizard.xml',
        'security/rules.xml',
        'account_view.xml',
        'base_view.xml',
        'distribution_costs_view.xml',
        'distribution_costs_sequence.xml',
        'product_data.xml',
        'product_view.xml',
        'report_intrastat_view.xml',
        'distribution_costs_workflow.xml',
        'wizard/stock_inventory_valuation.xml',
    ],
    'demo_xml': [],
    'test': [],
    #'external_dependancies': {'python': ['kombu'], 'bin': ['which']},
    'installable': True,
    'active': False,
    'license': 'AGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
