import frappe
from frappe.utils import flt,rounded,money_in_words
from frappe.model.mapper import get_mapped_doc
from frappe import throw, _
from erpnext.hr.doctype.process_payroll.process_payroll import get_month_details
import datetime

@frappe.whitelist()
def send_inspection_mail(item, inspector, name, verifier):
	try:
		subject = "Quality Inspection"
	 	message = """<p>Hello ,</p><p>Quality Inspection  : %s </p>
	 	<p> For Item: %s </p>
	 	<p>Inspected By : %s </p>"""%(name, item, inspector)
	 	recipients = inspector, verifier
	 	# frappe.sendmail(recipients=recipients, subject=subject, message =message)
	except Exception, e:
		import traceback
		print "notify", traceback.format_exc()
		return False


@frappe.whitelist()
def send_verified_mail(doc, method):
	if doc.verified:
		try:
			if doc.verified and doc.inspected_by:
				subject = "Quality Inspection Verified"
			 	message = """<p>Hello ,</p><p>Quality Inspection  : %s </p>
			 	<p> For Item: %s </p>
			 	<p>Verified By : %s </p>"""%(doc.name, doc.item_code, doc.verified )

			 	# frappe.sendmail(recipients=doc.verified, subject=subject, message =message)
		except Exception, e:
			import traceback
			print "notify", traceback.format_exc()
			return False

@frappe.whitelist()
def absent_days(employee, month, fiscal_year):
	m = get_month_details(fiscal_year, month)
	absent = frappe.db.sql("""
		select att_date from `tabAttendance` where employee = %s and status = "Absent" and att_date between %s and %s
		""", (employee, m.month_start_date, m.month_end_date), as_list=1)
	return len(absent)


@frappe.whitelist()
def activity_log(doc, method):
	stage_comm = ""
	probability_comm = ""
	reason_comm = []

	if (doc.contact_date != doc.old_date) or (doc.contact_date and not doc.old_date):
		doc.old_reason = doc.reason_for_changes
		doc.old_date = doc.contact_date
		if doc.contact_date:
			reason_comm.extend(("<b>Reason for Change:</b>", doc.reason_for_changes, "<br />"))
			reason_comm.extend(("Follow up contact date: ", doc.contact_date, "<br />"))
		
		if doc.follow_up_action:
			reason_comm.extend(("Next action : ", doc.follow_up_action, "<br />"))
		
		if doc.contact_by:
			reason_comm.extend(("Next Contact By: ", doc.contact_by, "<br />"))
	
	if (doc.opportunity_stage != doc.old_stage) or (doc.opportunity_stage and not doc.old_stage):
		doc.old_stage = doc.opportunity_stage
		stage_comm = """<b>Opportunity Stage:</b> """ + doc.opportunity_stage
		

	if (doc.probability != doc.old_probability) or (doc.probability and not doc.old_probability):
		doc.old_probability = doc.probability
		abc = "<b>Probability:</b> {0} %".format(doc.probability)
		print "\n\nabc",abc
		probability_comm = abc

	if reason_comm or stage_comm or probability_comm:
		comment = """<p>{0}</p> <p>{1}</p> <p>{2}</p>""".format(" ".join(reason_comm), stage_comm, probability_comm)
		doc.add_comment("Comment", comment)

@frappe.whitelist()
def check_attachment(doc, method):
	file_name = frappe.db.sql("""select file_name from `tabFile` where attached_to_name = '%s'"""%(doc.name), as_list=1)
	if not file_name:
		frappe.throw("Please Attach File")

@frappe.whitelist()
def add_actual_closure_date(doc, method):
	if(doc.items):
		if(doc.items[0].prevdoc_docname):
			quote=frappe.get_doc("Quotation",doc.items[0].prevdoc_docname)
			quote_link="<a href='desk#Form/Sales Order/"+doc.name+"'>"+doc.name+" </a>"
			quote.add_comment("Comment", "Quotation is closed against Sales Order: {0}".format(quote_link))
			quote.closer_date = datetime.datetime.now()
			quote.save()
			
@frappe.whitelist()
def add_actual_closure_date_in_quote(doc, method):
	if(doc.items):
		if(doc.items[0].prevdoc_docname):
			quote=frappe.get_doc("Opportunity",doc.items[0].prevdoc_docname)
			quote_link="<a href='desk#Form/Quotation/"+doc.name+"'>"+doc.name+" </a>"
			quote.add_comment("Comment", "Opportunity is closed against Quotation: {0}".format(quote_link))
			quote.closer_date = datetime.datetime.now()
			quote.save()

@frappe.whitelist()
def quot_workflow(doc, method):
	user = str(frappe.session['user'])
	user_role =  frappe.get_roles(user)
	
	price_list_amt = 0
	for row in doc.items:
		price_list_amt += row.qty * row.base_price_list_rate
	if (price_list_amt - doc.total) >= (price_list_amt)*20/100 and not "Sales Manager" in user_role:
		frappe.throw("Send this Quote to Sales Manager for Approval")
	if not "Sales Manager" in user_role and doc.discount_amount and (doc.discount_amount >= doc.total*20/100):
		frappe.throw("Send this Quote to Sales Manager for Approval")
	# elif "Sales Manager" in user_role or "Sales User" in user_role:
	# 	pass
	# else:
	# 	frappe.throw("Sales User or Sales Manager allow to submit")

@frappe.whitelist()
def calculate_tot_amount(doc, method):
	if doc.with_items:
		user = str(frappe.session['user'])
		user_role =  frappe.get_roles(user)
		tot_amount = 0
		for row in doc.items:
			if row.qty:
				price_list_rate = frappe.db.get_value("Item Price",{"item_code": row.item_code, "price_list": "Standard Selling"}, "price_list_rate")
				tot_amount += price_list_rate * row.qty
		doc.total_amount = tot_amount
		if (doc.total_amount and doc.estimated_sale_value) and (flt(doc.total_amount) > flt(doc.estimated_sale_value)) and not "Sales Manager" in user_role :
			frappe.throw("Total Amount must be less than Estimated Price")
		return tot_amount

@frappe.whitelist()
def make_order_register(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.customer = source.customer
		target.sales_order = source.name
		target.po_no = source.po_no
		target.po_date = source.po_date

	doclist = get_mapped_doc("Sales Order", source_name, {
			"Sales Order": {
				"doctype": "Service Request",
				"validation": {
					"docstatus": ["=", 1]
				}
			}
		}, target_doc, set_missing_values, ignore_permissions=False)
	return doclist

@frappe.whitelist()
def make_invoice(source_name, target_doc=None):
	def update_item(source, target, source_parent):
		count = frappe.db.sql(""" select 
					count(jcc_test.item_code) as count,
					group_concat(jcc_test.name) as jcc_test_detail,
					group_concat(jcc.name) as job_card
					from `tabSample Entry Register` ser, `tabService Request` sr, `tabJob Card Creation` jcc, `tabJob Card Creation Test Details` jcc_test 
					where ser.order_id=sr.name 
					and ser.job_card=jcc.name 
					and jcc_test.parent=jcc.name
					and sr.sales_order = %s
					and jcc_test.item_code = %s
		""", (source_name,source.item_code), as_list=1)
		# print "\n\ncount",count
		# print "\n\ncount",count[]
		# print "source_name",source_name
		# print "item_code",source.item_code
		target.base_amount = (flt(count[0][0]) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(count[0][0]) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = flt(count[0][0]) - flt(source.delivered_qty)
		target.job_card = count[0][2]
		target.job_card_test_reference = count[0][1]
		# frappe.msgprint("hiiiiii")

	def set_missing_values(source, target):
		target.customer = source.customer
		target.sales_order = source.name
		target.po_no = source.po_no
		target.po_date = source.po_date
		# frappe.msgprint("h111111111set")

	doclist = get_mapped_doc("Sales Order", source_name, {
			"Sales Order": {
				"doctype": "Sales Invoice",
				"validation": {
					"docstatus": ["=", 1]
				}
			},		
			"Sales Order Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"name": "so_detail",
					"parent": "sales_order",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.qty and (doc.base_amount==0 or doc.billed_amt < doc.amount)
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"add_if_empty": True
			},
			"Sales Team": {
				"doctype": "Sales Team",
				"add_if_empty": True
			}
		}, target_doc, set_missing_values, ignore_permissions=False)
	return doclist

@frappe.whitelist()
def bundle_so_present(doc,method):
	"""check sales order present for product bundle"""
	query = """select parent from `tabSales Order Item` where item_code = '%s'"""%(doc.name)
	so_of_bundle = frappe.db.sql(query,as_list=1)
	if so_of_bundle:
		so =  [i[0] for i in so_of_bundle]
		so_msg = "Product Bundle Linked with Sales Order "
		so_msg += ', '.join(so)
		frappe.throw(so_msg)
