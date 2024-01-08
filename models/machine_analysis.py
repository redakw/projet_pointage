# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    device_id = fields.Char(string='Biometric Device ID', help="Give the biometric device id")
    absence = fields.Integer(compute='_absence', store=True)
    zk_machine_attendance_ids = fields.One2many('zk.machine.attendance', 'employee_id')

    class Charge_pointage(models.Model):
        _name = 'charge.pointage'

        employee_id = fields.Many2one('hr.employee', string='')
        check_in = fields.Datetime()
        check_out = fields.Datetime()


    @api.depends('zk_machine_attendance_ids')
    def _absence(self):
        for employee in self:
            attendance_records = self.env['zk.machine.attendance'].search([
                ('employee_id', '=', employee.id),
                ('punching_time', '>=', fields.Date.context_today(self)),
                ('punching_time', '<', fields.Date.context_today(self) + timedelta(days=1))
            ])
            if attendance_records:
                employee.absence = 1
            else:
                employee.absence = 0

    def _update_employee_absence_cron(self):
        employees = self.search([])
        for employee in employees:
            employee._absence()
            
            
        # self.env['hr.employee.absence'].create({
        #   'employee_id': employee.id,
        #  'marked_absent': True
        # })
                
class ZkMachine(models.Model):
    _name = 'zk.machine.attendance'
    _inherit = 'hr.attendance'
    _order = 'punching_time desc,department_id'

    device_id = fields.Char(string='Biometric Device ID', help="Biometric device id")
    punch_type = fields.Selection([('1', 'Check In'),
                                   ('0', 'Check Out')],
                                  string='Punching Type')

    attendance_type = fields.Selection([('1', 'Finger'),
                                        ('15', 'Face'),
                                        ('2', 'Type_2'),
                                        ('3', 'Password'),
                                        ('4', 'Card')], string='Category', help="Select the attendance type")
    punching_time = fields.Datetime(string='Punching Time', help="Give the punching time")
    date = fields.Datetime()
    address_id = fields.Many2one('res.partner', string='Working Address', help="Address")
    bbol = fields.Boolean(compute='_compute_cnt')
    intt = fields.Integer()
    today_date = fields.Date(string="Aujourd'hui", compute='_compute_today_date')
    date_different_today = fields.Boolean(string="Date différente d'aujourd'hui", compute='_compute_date_difference', store= True)

    def _compute_today_date(self):
        for record in self:
            record.today_date = fields.Date.context_today(record)

    def _compute_date_difference(self):
        for record in self:
            if record.punching_time and record.today_date:
                record.date_different_today = record.punching_time.date() != record.today_date
            else:
                record.date_different_today = False
                
    # @api.depends('punching_time')
    def _compute_cnt(self):
        i=0
    # obj = self.env['zk.machine.attendance'].search([])
    # for val in obj:
        for rec in self:
            if (i % 2) ==0:
                print("valeur:",i)
                rec.bbol=1
            else:
                rec.bbol=0
            i=i+1
            

    # ligne = val.punching_time
    # val =val.id+1
    # ligne_s = val.punching_time
    # if val[id].punching_time:
    # print ('falll'val[id])
    # val.intt=val[+1].id
    # raise ValidationError(val.punching_time)

    # val.date= val[id].punching_time - val[id+1].punching_time
    # else:
    # val.date =datetime.datetime.now()
    # raise ValidationError()


class ReportZkDevice(models.Model):
    _name = 'zk.report.daily.attendance'
    _auto = False
    _order = 'punching_day desc'

    name = fields.Many2one('hr.employee', string='Employee', help="Employee")
    punching_day = fields.Datetime(string='Date', help="Punching Date")
    address_id = fields.Many2one('res.partner', string='Working Address')
    attendance_type = fields.Selection([('1', 'Finger'),
                                        ('15', 'Face'),
                                        ('2', 'Type_2'),
                                        ('3', 'Password'),
                                        ('4', 'Card')],
                                       string='Category', help="Select the attendance type")
    punch_type = fields.Selection([('0', 'Check In'),
                                   ('1', 'Check Out'),
                                   ('2', 'Break Out'),
                                   ('3', 'Break In'),
                                   ('4', 'Overtime In'),
                                   ('5', 'Overtime Out')], string='Punching Type', help="Select the punch type")
    punching_time = fields.Datetime(string='Punching Time', help="Punching Time")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'zk_report_daily_attendance')
        query = """
            create or replace view zk_report_daily_attendance as (
                select
                    min(z.id) as id,
                    z.employee_id as name,
                    z.write_date as punching_day,
                    z.address_id as address_id,
                    z.attendance_type as attendance_type,
                    z.punching_time as punching_time,
                    z.punch_type as punch_type
                from zk_machine_attendance z
                    join hr_employee e on (z.employee_id=e.id)
                GROUP BY
                    z.employee_id,
                    z.write_date,
                    z.address_id,
                    z.attendance_type,
                    z.punch_type,
                    z.punching_time
            )
        """
        self._cr.execute(query)

class Zk_Hr_attendence(models.Model):
    _inherit = 'hr.attendance'

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """overriding the __check_validity function for employee attendance."""
        pass
