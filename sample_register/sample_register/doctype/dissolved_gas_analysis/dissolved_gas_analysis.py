# -*- coding: utf-8 -*-
# Copyright (c) 2015, indictrans and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import datetime
from sample_register.sample_register.trb_common import check_bottle_no,check_open_trb_batch_count

class DissolvedGasAnalysis(Document):
	def on_submit(self):
		check_open_trb_batch_count(self.trb_batch)
		self.set_job_card_status()
		self.end_time = datetime.datetime.now()
		if self.result_status == "Reject":
			current_trb = frappe.get_doc("Dissolved Gas Analysis", self.name)
			new_trb = frappe.copy_doc(current_trb, ignore_no_copy=False)
			new_trb.remarks = " created from "+self.name
			new_trb.gase_analysis_run1 = []
			new_trb.gas_analysis_run_2 = []
			new_trb.analysis_run1 = []
			new_trb.analysis_run2 = []
			new_trb.trb_batch = ""
			new_trb.result_status = ""
			new_trb.save()

	def set_job_card_status(self):
		if not self.result_status:
			frappe.throw("Please Enter status")
		if self.result_status and (self.result_status == "Accept" or self.result_status == "Reject" or self.result_status == "Select"):
			print "\n\nin validate"
			cond = """select name from `tabJob Card Creation Test Details` where parent = '%s'"""%(self.job_card)
			if self.test_group:
				cond += """ and test_group = '%s'"""%(self.test_group)
			if self.item_code:
				cond += """ and item_code = '%s'"""%(self.item_code)
			if self.item_name:
				cond += """ and item_name = '%s'"""%(self.item_name)
	
			job_card_details = frappe.db.sql(cond, as_dict=1)
			jc_name = job_card_details[0]['name']
			print "\n\njcname",jc_name
			update_query = ("""
								update 
									`tabJob Card Creation Test Details` 
								set 
									status = '{0}', test_name = '{1}'
								where 
									name = '{2}'
							""".format(self.result_status,self.name,jc_name))
			frappe.db.sql(update_query)
		
		job_card = frappe.get_doc("Job Card Creation", self.job_card)
		status = True
		for test in job_card.test_details:
			if test.status != "Accept":
				status = False
		if status == True:
			frappe.db.set_value("Job Card Creation", self.job_card, "status", "Accept")
			frappe.db.set_value("Sample Entry Register", self.sample_id, "job_card_trb_status", "Accept")

	def validate(self):
		self.set_job_card_status()
		dl_dga = frappe.db.sql("""select container_id from `tabContainer Details`\
			where parent = '{0}'""".format(self.sample_id), as_list=1)
		b =[e[0] for e in dl_dga]
		if self.bottle_number:
			if self.bottle_number in b:
				pass
			else:
				frappe.msgprint("Please check bottle number {0} with container id entered in Sample Register Entry: {1}.".format(self.bottle_number,self.sample_id))