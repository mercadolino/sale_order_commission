
from openerp import tools
from openerp.osv import fields, osv
from datetime import datetime
from openerp.tools.translate import _


class product_commission_rule(osv.osv):
    _inherit = 'product.product' 
    #Do not touch _name it must be same as _inherit
    #_name = 'product.product'
    
    
    _columns = {
            'commission_type':fields.selection([('percentage','Percentage'),
                ('fixed','Fixed Value'),
                 ],    'Commission Type', select=True, readonly=False, required=True),
            'driver_commission': fields.float('Driver Commission'),
            'helper_commission': fields.float('Driver Commission'),
                    }
            
    _defaults = {  
                'driver_commission': 0,
                'helper_commission': 0,
                'type':'percentage',    
                }
    
    
class sale_order_commission(osv.osv):
    _name = 'sale.order.commission'
    _description = 'Sales order commission'
    _columns = {
            'employee_id':fields.many2one(obj='hr.employee', string='Employee', required=True),
            'sale_order_id':fields.many2one(obj='sale.order', string='Sale Order', required=True),
            # TODO : import time required to get current date
            'sale_date': fields.date(string='Sale Date'),      
            'sale_order_value': fields.float(string='Sale Value'),
            'num_transport': fields.integer('Transported Quantity'),
            'commission_value': fields.float(string='Commission Value'),
            'state':fields.selection([('draft','Draft'),('confirmed','Confirmed'),('paid','Paid'),('canceled','Canceled')],
                                     'State', select=True, readonly=True),
            'payment_ref':fields.char(string='Payment Ref', size=64, required=False, readonly=False,
                                      help=_('Reference to payslip number')),            
            'payment_date': fields.date(string='Payment Date',
                                        help=_('Date when the commission was paid in PaySlip')),
                    }
    _defaults = {  
        'state': 'draft'
        }    
       
    def employee_id_change(self, cr, uid, ids, employee_id, context):
        result = {}
        sale_order = self.pool.get('sale.order').browse(cr, uid, context.get('sale_order_id'))
        
        if sale_order:            
            employee_num_transport = [ fleet.cargo_ids for fleet in sale_order.fleet_vehicles_ids
                 if (employee_id == fleet.employee_driver_id.id 
                     or employee_id == fleet.employee_helper_id.id)]
            if not employee_num_transport:
                raise osv.except_osv(_('Warning'), _("No Transport information was found for this employee.\n Please, verify he belongs to the transport sale!"))
                        
            result['num_transport'] = sum( len(l) for l in employee_num_transport)
            #result['sale_order_value'] = sale_order.amount_untaxed
                             
        return {'value':result}
    
    #Validates if the add employee commission exists in fleet vehicle transport
    def _validate_employee_transport(self,cr,uid,ids):
        
        result = False                
        
        commission = self.browse(cr,uid,ids[0])       
        
        if commission:
            #sale_order = self.pool.get('sale.order').browse(cr,uid,commission.sale_order_id.id)
            transports = commission.sale_order_id.fleet_vehicles_ids
            if transports:
                drivers_ids = [transport.employee_driver_id.id for transport in transports]
                helpers_ids = [transport.employee_helper_id.id for transport in transports]
            
                if commission.employee_id.id in drivers_ids + helpers_ids:
                    result = True
            else:
                result = True
        return result
    
    def copy(self, cr, uid, _id, default=None, context=None): 
                
        if not default:
            default = {}
            default.update({
            'state': 'draft',
            })
        
        result = super(sale_order_commission, self).copy(cr, uid, _id, default, context)
        return result 
    
    #_constraints = [(_validate_employee_transport,_("Error: There a Employee that is not in transport information!"), ['employee_id'])]
    
class sale_commission_individual_report(osv.osv):
    _name = "sale.order.commission_individual_report"
    _description = 'Sale Order Commission Statistics'
    _auto = False
     
    _columns = {
                'employee_id':fields.many2one(obj='hr.employee', string='Employee', required=True,readonly=True),
                'year': fields.char('Year', size=4, readonly=True),
                'month': fields.selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
                                            ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'), ('09', 'September'),
                                            ('10', 'October'), ('11', 'November'), ('12', 'December')], string='Month', readonly=True),
                'sale_order_value': fields.float(string='Sale Value',readonly=True),
                'num_of_sale': fields.integer('Total Sale',readonly=True),
                'total_commission_value': fields.float(string='Total Commission Value',readonly=True),
                    }

    def init(self, cr):
        
        tools.drop_view_if_exists(cr, 'sale_order_commission_individual_report')
        
        cr.execute("""
         CREATE OR REPLACE VIEW sale_order_commission_individual_report AS (
            SELECT                
                min(soc.id) AS id,
                soc.employee_id AS employee_id,
                to_char(soc.sale_date, 'YYYY') AS year,
                    to_char(soc.sale_date, 'MM') AS month,        
                    count(soc.id) AS num_of_sale,
                    sum(soc.commission_value) AS total_commission_value 
            FROM sale_order_commission soc
            JOIN hr_employee hre ON soc.employee_id=hre.id 
                AND (soc.state ='confirmed' OR soc.state = 'paid')
            GROUP BY         
                to_char(soc.sale_date, 'YYYY'),
                to_char(soc.sale_date, 'MM'),
                soc.employee_id
            ORDER BY
                to_char(soc.sale_date, 'YYYY'),
                to_char(soc.sale_date, 'MM'),
                soc.employee_id
            )
""")
         
    
class sale_order(osv.osv):
    _inherit = 'sale.order'    
    # Do not touch _name it must be same as _inherit
    # _name = 'sale.order'
    _columns = {
            'commission_ids':fields.one2many(obj='sale.order.commission',
                     fields_id='sale_order_id', string='Commissions', required=False),
                }
    
    def calculate_commission(self,cargo_ids,is_driver):
        commission = 0
        for cargo in cargo_ids:
            product_id = cargo.cargo_product_id
            if product_id.commission_type == 'percentage':
                if is_driver:
                    commission += product_id.list_price - product_id.driver_commission*product_id.list_price
                else:                    
                    commission += product_id.list_price - product_id.helper_commission*product_id.list_price                   
            else:
                if is_driver:
                    commission += cargo.product_id.driver_commission
                else:
                    commission += cargo.product_id.helper_commission
        return commission
    
    def write(self, cr, uid, ids, vals, context=None):
                
        commission_vals={}
        
        if vals.get('state',False):
            commission_ids = self.pool.get('sale.order.commission').search(cr, uid,[('sale_order_id','=',ids[0])],order='sale_date' )
        
            if commission_ids:        
                commission_obj = self.pool.get('sale.order.commission')                            
                if vals['state'] == 'done' or vals['state'] == 'manual'or vals['state'] == 'progress':
                    commission_vals['state'] ='confirmed'                       
                    commission_vals['sale_date'] = datetime.now().strftime('%Y-%m-%d')                
                if vals['state'] == 'cancel':
                    commission_vals['state'] ='canceled'              
                if commission_vals:
                    commission_obj.write(cr,uid,commission_ids,commission_vals,context=context)
              
        return super(sale_order, self).write(cr, uid, ids, vals, context=context)
        
    def generate_commission(self, cr, uid, ids, context=None):                
        
        fleet_vehicles_ids = self.browse(cr,uid,ids[0]).fleet_vehicles_ids;       
        commissions_list = []
                                    
        for vehicle in fleet_vehicles_ids:
            
            driver_commission = {}
            driver_commission['employee_id'] = vehicle.employee_driver_id.id
            driver_commission['num_transport'] =  len(vehicle.cargo_ids)
            driver_commission['sale_order_id'] = vehicle.sale_order_id.id                
            driver_commission['commission_value'] = self.calculate_commission(vehicle.id,vehicle.cargo_ids,True)
            commissions_list.append(driver_commission)
            
            if vehicle.employee_helper_id:
                helper_commission = {}
                
                helper_commission['employee_id'] = vehicle.employee_helper_id.id
                helper_commission['num_transport'] =  len(vehicle.cargo_ids)
                helper_commission['sale_order_id'] =  vehicle.sale_order_id.id                
                helper_commission['commission_value'] = self.calculate_commission(vehicle.id,vehicle.cargo_ids,False)
                commissions_list.append(helper_commission)
        
        commission_obj = self.pool.get('sale.order.commission')
        
        commission_obj.create(cr, uid, commissions_list, context=None)
        return
    
class hr_commission(osv.osv):
    _inherit = 'hr.employee' 
    # Do not touch _name it must be same as _inherit
    # _name = 'hr.employee'
    _columns = {
            'commission_ids':fields.one2many(obj='sale.order.commission', fields_id='employee_id',
                                             string='Commission', required=False),
            'commission_ind_report_ids':fields.one2many(obj='sale.order.commission_individual_report',
                                                        fields_id='employee_id', string='Commission Individual Report', required=False),
                    }
    
    # Get all commission from a employee from a data range
    def get_commission(self, cr, uid, ids, employee_id, from_date, to_date, context=None):

        range_commission_ids = self.pool.get('sale.order.commission').search(cr,uid,['&',('employee_id','=',employee_id),
                  '&',('sale_date','>=',from_date),
                  '&',('sale_date','<=',to_date),
                  ('state','=','confirmed')],order='sale_date')
        
        commissions = self.pool.get('sale.order.commission').browse(cr,uid,range_commission_ids)
        
        commission_value = sum(commission.commission_value for commission in commissions)        
        
        return commission_value
    
    # After payslip be approved this method must be called to set all commission in the payslip to be 
    # marked as paid and add the payment reference
    def set_commission_paid(self, cr, uid, employee_id, payslip_ref, payment_date,from_date, to_date, context):
        
        range_commission_ids = self.pool.get('sale.order.commission').search(cr,uid,['&',('employee_id','=',employee_id),
                  '&',('sale_date','>=',from_date),
                  '&',('sale_date','<=',to_date),
                  ('state','=','confirmed')],order='sale_date')            
        
        vals= {}
        vals['state'] = 'paid'
        vals['payment_date'] = payment_date
        vals['payment_ref'] = payslip_ref
        
        return self.pool.get('sale.order.commission').write(cr, uid, range_commission_ids, vals, context=context)
    
    
    def reset_commission(self, cr, uid, payslip_ref, context):
        
        range_commission_ids = self.pool.get('sale.order.commission').search(cr,uid,[('payment_ref','=',payslip_ref)], order='sale_date')            
        
        vals= {}
        vals['state'] = 'confirmed'
        vals['payment_ref'] = None
        vals['payment_date'] = None
        
        return self.pool.get('sale.order.commission').write(cr, uid, range_commission_ids, vals, context=context)
    
class payslip_commission(osv.osv):
    _inherit = 'hr.payslip'
    
    def process_sheet(self, cr, uid, ids, context=None):
        compute_sheet_return = super(payslip_commission, self).process_sheet(cr, uid, ids, context)
        if compute_sheet_return:
            slip_instance = self.browse(cr, uid, ids[0])
            slip_reference = slip_instance.number
            slip_date_from = slip_instance.date_from
            slip_date_to = slip_instance.date_to
            slip_payment_date = datetime.now().strftime('%Y-%m-%d')
            slip_employee_id = slip_instance.employee_id.id
            self.pool.get('hr.employee').set_commission_paid(cr, uid, slip_employee_id, slip_reference, slip_payment_date, slip_date_from, slip_date_to, context)
        return compute_sheet_return
    
    def write(self, cr, uid, ids, vals, context=None):
        slip_instance = self.browse(cr, uid, ids[0])
        slip_reference = slip_instance.number
        #slip_employee_id = slip_instance.employee_id.id
        if slip_instance.state == 'done' and not slip_instance.canceled and vals['canceled'] == True:          
            self.pool.get('hr.employee').reset_commission(cr, uid, slip_reference, context)
        write_return = super(payslip_commission, self).write(cr, uid, ids, vals, context=context)
        return write_return
        
                        
