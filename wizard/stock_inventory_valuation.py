# -*- coding: utf-8 -*-
##############################################################################
#
#    distribution_costs module for OpenERP, Computes average purchase price from invoices and misc costs
#    Copyright (C) 2012 SYLEAM Info Services (<http://www.syleam.fr/>)
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

from osv import osv
from osv import fields


class wizard_inventory_valuation(osv.osv_memory):
    _name = 'wizard.inventory.valuation'
    _description = 'Compute Inventory Valuation'

    _columns = {
        'date_valuation': fields.date('Date of inventory valuation', required=True, help='Date of Stock Inventory Valuation'),
    }

    def compute_inventory_valuation(self, cr, uid, ids, data, context=None):
        for wizard in self.browse(cr, uid, ids, context=context):
            cr.execute(
                """
                    DO $$
                        DECLARE
                            record1 record;
                            record2 record;
                        BEGIN
                            -- Research stock
                            TRUNCATE TABLE stock_inventory_valuation;
                            FOR record1 IN
                                SELECT max(report.id) AS id, (SELECT stock_location.warehouse_id FROM stock_location WHERE stock_location.id = report.location_id) AS warehouse_id, report.product_id, report.location_id, (SELECT product_template.uom_id FROM product_product, product_template WHERE product_product.product_tmpl_id = product_template.id AND product_product.id = report.product_id) AS uom_id, sum(report.qty) AS product_qty
                                FROM (
                                    SELECT - max(sm.id) AS id, sm.location_id, sm.product_id, - sum(sm.product_qty / uo.factor) AS qty
                                    FROM stock_move sm
                                    LEFT JOIN stock_location sl ON sl.id = sm.location_id
                                    LEFT JOIN product_product pp ON pp.id = sm.product_id
                                    LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                                    LEFT JOIN product_uom uo ON uo.id = sm.product_uom
                                    WHERE sm.state::text = 'done'::text
                                    AND sm.location_id <> sm.location_dest_id
                                    AND (sm.location_id IN ( SELECT stock_location.id FROM stock_location WHERE stock_location.usage::text = 'internal'::text))
                                    AND pp.active = true
                                    AND pt.type = 'product'
                                    AND sm.date::date <= %s
                                    GROUP BY sm.location_id, sm.product_id, sm.product_uom
                                    UNION ALL
                                    SELECT max(sm.id) AS id, sm.location_dest_id AS location_id, sm.product_id, sum(sm.product_qty / uo.factor) AS qty
                                    FROM stock_move sm
                                    LEFT JOIN stock_location sl ON sl.id = sm.location_dest_id
                                    LEFT JOIN product_product pp ON pp.id = sm.product_id
                                    LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                                    LEFT JOIN product_uom uo ON uo.id = sm.product_uom
                                    WHERE sm.state::text = 'done'::text
                                    AND sm.location_id <> sm.location_dest_id
                                    AND (sm.location_dest_id IN ( SELECT stock_location.id FROM stock_location WHERE stock_location.usage::text = 'internal'::text))
                                    AND pp.active = true
                                    AND pt.type = 'product'
                                    AND sm.date::date <= %s
                                    GROUP BY sm.location_dest_id, sm.product_id, sm.product_uom
                                ) report
                                GROUP BY report.location_id, report.product_id
                                HAVING sum(report.qty) > 0::numeric
                            LOOP
                                -- Research incoming the final movement for each product
                                SELECT INTO record2 sm.product_id, sm.average_price
                                FROM stock_move sm
                                LEFT JOIN stock_location sl ON sl.id = sm.location_id
                                LEFT JOIN stock_location sldest ON sldest.id = sm.location_dest_id
                                WHERE sm.location_id <> sm.location_dest_id
                                AND sm.state::text = 'done'::text
                                AND sl.usage::text NOT IN ('internal', 'customer')
                                AND sldest.usage::text = 'internal'::text
                                AND sm.product_id = record1.product_id
                                AND sm.date::date <= %s
                                ORDER BY sm.date DESC
                                LIMIT 1;

                                INSERT INTO stock_inventory_valuation(
                                    create_uid,
                                    create_date,
                                    date,
                                    product_id,
                                    qty,
                                    uom_id,
                                    warehouse_id,
                                    location_id,
                                    standard_price,
                                    cost_price
                                )
                                VALUES (
                                    1,
                                    now(),
                                    %s,
                                    record2.product_id,
                                    record1.product_qty,
                                    record1.uom_id,
                                    record1.warehouse_id,
                                    record1.location_id,
                                    record2.average_price,
                                    record2.average_price * record1.product_qty
                                );

                            END LOOP;
                        END;
                    $$;
                """, (wizard.date_valuation, wizard.date_valuation, wizard.date_valuation, wizard.date_valuation))
        ir_obj = self.pool.get('ir.model.data')
        action_model, action_id = ir_obj.get_object_reference(cr, uid, 'distribution_costs', 'act_open_stock_inventory_valuation_view')
        action_data = self.pool.get(action_model).read(cr, uid, action_id, [], context=context)
        return action_data

wizard_inventory_valuation()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
