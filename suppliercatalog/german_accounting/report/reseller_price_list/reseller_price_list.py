import frappe
from frappe import _
from frappe.query_builder import DocType, functions as fn


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_settings():
	settings = frappe.get_single("Reseller Pricelist Settings")
	return {
		"purchase": settings.net_ek_pricelist,
		"reseller": settings.net_reseller_pricelist,
		"gross_sales": settings.gross_vk_pricelist,
		"net_sales": settings.net_vk_pricelist,
	}


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "item_code",
			"label": _("Item Name"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 150
		},
		{
			"fieldname": "item_group",
			"label": _("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 130
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150
		},
		{
			"fieldname": "purchase_price",
			"label": _("Purchase Price"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "reseller_price",
			"label": _("Reseller Price"),
			"fieldtype": "HTML",
			"width": 120
		},
		{
			"fieldname": "gross_sales_price",
			"label": _("Gross Sales Price"),
			"fieldtype": "HTML",
			"width": 130
		},
		{
			"fieldname": "discount_percent",
			"label": _("Discount %"),
			"fieldtype": "HTML",
			"width": 100
		},
		{
			"fieldname": "reseller_item",
			"label": _("Reseller Item"),
			"fieldtype": "HTML",
			"width": 100
		},
		{
			"fieldname": "selling_stop",
			"label": _("Selling Stop"),
			"fieldtype": "HTML",
			"width": 100
		}
	]


def get_data(filters):
	"""Fetch report data using Query Builder"""
	Item = DocType("Item")
	ItemSupplier = DocType("Item Supplier")
	ItemPrice = DocType("Item Price")

	# Build base query - each row is an item-supplier combination
	query = (
		frappe.qb.from_(Item)
		.left_join(ItemSupplier)
		.on(ItemSupplier.parent == Item.name)
		.select(
			Item.name.as_("item_code"),
			Item.item_name,
			Item.item_group,
			ItemSupplier.supplier,
			Item.custom_reseller_item.as_("reseller_item"),
			Item.custom_selling_stop.as_("selling_stop")
		)
		.where(Item.disabled == 0)
		.orderby(Item.name)
		.orderby(ItemSupplier.idx)
	)

	# Apply filters
	if filters.get("item_group"):
		query = query.where(Item.item_group == filters.get("item_group"))

	if filters.get("supplier"):
		query = query.where(ItemSupplier.supplier == filters.get("supplier"))

	if filters.get("reseller_item"):
		query = query.where(Item.custom_reseller_item == 1)

	if filters.get("selling_stop"):
		query = query.where(Item.custom_selling_stop == 1)

	# Execute query
	items = query.run(as_dict=True)

	# Get price list settings
	settings = get_settings()

	# Enrich data with price information and editable fields
	data = []
	for item in items:
		item_data = item.copy()
		item_code = item.item_code

		# Get prices using settings
		purchase_price = get_item_price(item_code, settings["purchase"])
		reseller_price = get_item_price(item_code, settings["reseller"])
		gross_sales_price = get_item_price(item_code, settings["gross_sales"])
		net_sales_price = get_item_price(item_code, settings["net_sales"])

		item_data["purchase_price"] = purchase_price

		# Editable Reseller Price
		item_data["reseller_price"] = f'''<input 
			id="reseller_price_{item_code}" 
			class="form-control" 
			pattern="[0-9]+(\.[0-9]{{1,2}})?" 
			type="text" 
			inputmode="decimal"
			value="{reseller_price}" 
			onchange="update_reseller_price('{item_code}', '{settings['reseller']}', this.value)"
			style="width: 100px;">'''

		# Editable Gross Sales Price
		item_data["gross_sales_price"] = f'''<input 
			id="gross_sales_price_{item_code}" 
			class="form-control" 
			type="text" 
			pattern="[0-9]+(\.[0-9]{{1,2}})?" 
			inputmode="decimal"
			value="{gross_sales_price}" 
			onchange="update_gross_sales_price('{item_code}', '{settings['gross_sales']}', this.value)"
			style="width: 100px;">'''

		# Calculate discount percentage
		discount_percent = 0
		if reseller_price and net_sales_price and net_sales_price > 0:
			discount_percent = ((net_sales_price - reseller_price) / net_sales_price) * 100

		# Editable Discount %
		item_data["discount_percent"] = f'''<input 
			id="discount_percent_{item_code}" 
			class="form-control" 
			type="text" 
			pattern="[0-9]+(\.[0-9]{{1,2}})?" 
			inputmode="decimal"
			value="{discount_percent:.2f}" 
			onchange="update_discount_percent('{item_code}', this.value)"
			style="width: 80px;">'''

		# Editable Reseller Item checkbox
		checked_reseller = "checked" if item.reseller_item else ""
		item_data["reseller_item"] = f'''<input 
			id="reseller_item_{item_code}" 
			type="checkbox" 
			{checked_reseller}
			onchange="update_item_field('{item_code}', 'custom_reseller_item', this.checked ? 1 : 0)">'''

		# Editable Selling Stop checkbox
		checked_stop = "checked" if item.selling_stop else ""
		item_data["selling_stop"] = f'''<input 
			id="selling_stop_{item_code}" 
			type="checkbox" 
			{checked_stop}
			onchange="update_item_field('{item_code}', 'custom_selling_stop', this.checked ? 1 : 0)">'''

		data.append(item_data)

	return data


def get_item_price(item_code, price_list_name):
	"""Get item price from specific price list using Query Builder"""
	ItemPrice = DocType("Item Price")

	query = (
		frappe.qb.from_(ItemPrice)
		.select(ItemPrice.price_list_rate)
		.where(
			(ItemPrice.item_code == item_code) &
			(ItemPrice.price_list == price_list_name)
		)
		.orderby(ItemPrice.modified, order=frappe.qb.desc)
		.limit(1)
	)

	result = query.run(as_dict=True)
	return result[0].price_list_rate if result else 0


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_suppliers_from_items(doctype, txt, searchfield, start, page_len, filters):
	ItemSupplier = DocType("Item Supplier")
	Supplier = DocType("Supplier")

	min_idx_subquery = (
		frappe.qb.from_(ItemSupplier)
		.select(
			ItemSupplier.parent,
			fn.Min(ItemSupplier.idx).as_("min_idx")
		)
		.where(ItemSupplier.parenttype == "Item")
		.groupby(ItemSupplier.parent)
	).as_("min_supplier")

	query = (
		frappe.qb.from_(ItemSupplier)
		.inner_join(min_idx_subquery)
		.on(
			(ItemSupplier.parent == min_idx_subquery.parent) &
			(ItemSupplier.idx == min_idx_subquery.min_idx)
		)
		.inner_join(Supplier)
		.on(Supplier.name == ItemSupplier.supplier)
		.select(
			ItemSupplier.supplier,
			Supplier.supplier_name,
			Supplier.supplier_group
		)
		.distinct()
		.where(
			(ItemSupplier.parenttype == "Item") &
			(ItemSupplier.supplier.like(f"%{txt}%"))
		)
		.orderby(ItemSupplier.supplier)
		.limit(page_len)
		.offset(start)
	)

	result = query.run()
	return result


@frappe.whitelist()
def update_item_price(item_code, price_list_name, new_price):
	"""Update or create Item Price for given item and price list"""
	try:
		new_price = float(new_price) if new_price else 0
		doc_name = None
		action = None
		
		# Check if Item Price exists
		existing = frappe.db.get_value(
			"Item Price",
			{
				"item_code": item_code,
				"price_list": price_list_name
			},
			["name"]
		)
		
		if existing:
			# Update existing
			frappe.db.set_value("Item Price", existing, "price_list_rate", new_price)
			doc_name = existing
			action = "updated"
		else:
			# Create new Item Price
			doc = frappe.get_doc({
				"doctype": "Item Price",
				"item_code": item_code,
				"price_list": price_list_name,
				"price_list_rate": new_price
			})
			doc.insert(ignore_permissions=True)
			doc_name = doc.name
			action = "created"
		
		frappe.db.commit()
		return {
			"success": True,
			"doc_name": doc_name,
			"doctype": "Item Price",
			"action": action
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Update Item Price Error")
		frappe.throw(_("Error updating price: {0}").format(str(e)))


@frappe.whitelist()
def update_item_field(item_code, field_name, value):
	"""Update custom fields on Item doctype"""
	try:
		valid_fields = ["custom_reseller_item", "custom_selling_stop"]
		if field_name not in valid_fields:
			frappe.throw(_("Invalid field name"))
		
		value = 1 if value == "1" or value == 1 or value is True else 0
		frappe.db.set_value("Item", item_code, field_name, value)
		frappe.db.commit()
		return {
			"success": True,
			"doc_name": item_code,
			"doctype": "Item",
			"action": "updated"
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Update Item Field Error")
		frappe.throw(_("Error updating field: {0}").format(str(e)))


@frappe.whitelist()
def update_reseller_price_by_discount(item_code, discount_percent):
	"""Calculate and update reseller price based on discount percentage"""
	try:
		discount_percent = float(discount_percent) if discount_percent else 0
		settings = get_settings()
		
		# Get net sales price
		net_sales_price = get_item_price(item_code, settings["net_sales"])
		
		if not net_sales_price or net_sales_price <= 0:
			frappe.throw(_("Net Sales Price must be greater than 0 to calculate discount"))
		
		# Calculate reseller price: Reseller Price = Net Sales Price * (1 - Discount% / 100)
		new_reseller_price = net_sales_price * (1 - (discount_percent / 100))
		
		# Update the reseller price and get the document info
		result = update_item_price(item_code, settings["reseller"], new_reseller_price)
		
		return {
			"success": True,
			"new_reseller_price": new_reseller_price,
			"net_sales_price": net_sales_price,
			"discount_percent": discount_percent,
			"doc_name": result.get("doc_name"),
			"doctype": result.get("doctype"),
			"action": result.get("action")
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Update Reseller Price by Discount Error")
		frappe.throw(_("Error calculating price: {0}").format(str(e)))