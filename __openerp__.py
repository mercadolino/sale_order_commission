{
    "name": "Sales Order Commission",
    "version": "1.0",
    "depends": ["base","fleet","sale","transport_sale","hr_payroll"],
    "author": "Alien Group Lda",
    'website':'http://www.snippetbucket.com',
    "category": "Sales Management",
    "description": """
    This module provide :
    Support for commission for the employees (Driver) related to
    Transport services. Also used to calculate the driver production
    based on number os transport and commission
    related to a transport order
    """,
    'data':['sale_order_commission_view.xml','security/ir.model.access.csv'],
    #'test':['test/employee_get_commission.yml'],
    'installable': True,

}
