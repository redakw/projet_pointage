# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2020-TODAY Cybrosys Technologies(<http://www.cybrosys.com>).
#    Author: cybrosys(<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################
import pytz
import sys
import datetime
import logging
import binascii

from . import zklib
from .zkconst import *
from struct import unpack
from odoo import api, fields, models
from odoo import _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please Install pyzk library.")

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    device_id = fields.Char(string='Biometric Device ID')

    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        pass


class ZkMachine(models.Model):
    _name = 'zk.machine'

    name = fields.Char(string='Machine IP', required=True)
    port_no = fields.Integer(string='Port No', required=True)
    address_id = fields.Many2one('res.partner', string='Working Address')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)

    def device_connect(self, zk):
        try:
            conn = zk.connect()
            return conn
        except:
            return False

    def test(self):
        print("bonjour test")
    def clear_attendance(self):
        for info in self:
            try:
                machine_ip = info.name
                zk_port = info.port_no
                timeout = 30
                try:
                    zk = ZK(machine_ip, port=zk_port, timeout=timeout, password=0, force_udp=False, ommit_ping=False)
                except NameError:
                    raise UserError(_("Please install it with 'pip3 install pyzk'."))
                conn = self.device_connect(zk)
                if conn:
                    conn.enable_device()
                    clear_data = zk.get_attendance()
                    if clear_data:
                        # conn.clear_attendance()
                        self._cr.execute(""" """)
                        # self._cr.execute("""delete from zk_machine_attendance""")
                        conn.disconnect()
                        raise UserError(_('Attendance Records Deleted.'))
                    else:
                        raise UserError(_('Unable to clear Attendance log. Are you sure attendance log is not empty.'))
                else:
                    raise UserError(
                        _('Unable to connect to Attendance Device. Please use Test Connection button to verify.'))
            except:
                raise ValidationError(
                    'Unable to clear Attendance log. Are you sure attendance device is connected & record is not empty.')

    def getSizeUser(self, zk):
        """Checks a returned packet to see if it returned CMD_PREPARE_DATA,
        indicating that data packets are to be sent

        Returns the amount of bytes that are going to be sent"""
        command = unpack('HHHH', zk.data_recv[:8])[0]
        if command == CMD_PREPARE_DATA:
            size = unpack('I', zk.data_recv[8:12])[0]
            return size
        else:
            return False

    def zkgetuser(self, zk):
        """Start a connection with the time clock"""
        try:
            users = zk.get_users()
            return users
        except:
            return False

    @api.model
    def cron_download(self):
        machines = self.env['zk.machine'].search([])
        for machine in machines:
            machine.download_attendance()


    def download_attendance(self):
        zk_attendance_records = self.env['zk.machine.attendance'].search([])#affectation d objet  zk.machine.attendance

        for employee_id in zk_attendance_records.mapped('employee_id'): # boucle sur zk_attendance_records et amene les employés .mapped(amane les employés une seul fois uniqueùent mem s'il se repete plusieurs fois dans zk_attendance_records)
            employee_attendances = zk_attendance_records.filtered(lambda e: e.employee_id == employee_id)# ici j ai amené le pointage de chaque employee
            dates = set(attendance.punching_time.date() for attendance in employee_attendances)

            for date in dates:
                date_attendances = employee_attendances.filtered(lambda r: r.punching_time.date() == date)

                check_in = min(date_attendances.mapped('punching_time'))
                check_out = max(date_attendances.mapped('punching_time'))

                # Check if check_in and check_out are on different dates
                if check_in.date() != check_out.date():
                    # Create two separate records for night shift
                    night_shift_check_out = datetime.combine(check_in.date() + timedelta(days=1), datetime.min.time())

                    hr_attendance_record_night_shift = self.env['hr.attendance'].create({
                        'employee_id': employee_id.id,
                        'check_in': check_in,
                        'check_out': night_shift_check_out,
                    })

                    hr_attendance_record_day_shift = self.env['hr.attendance'].create({
                        'employee_id': employee_id.id,
                        'check_in': datetime.combine(check_out.date(), datetime.min.time()),
                        'check_out': check_out,
                    })
                else:
                    hr_attendance_record = self.env['hr.attendance'].search([
                        ('employee_id', '=', employee_id.id),
                        ('check_in', '<=', check_out),
                        ('check_out', '>=', check_in),
                    ])

                    if not hr_attendance_record:
                        hr_attendance_record = self.env['hr.attendance'].create({
                            'employee_id': employee_id.id,
                            'check_in': check_in,
                            'check_out': check_out,
                        })
                    else:
                        hr_attendance_record.write({
                            'check_in': check_in,
                            'check_out': check_out,
                        })








