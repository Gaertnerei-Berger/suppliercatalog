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
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "gross_sales_price",
			"label": _("Gross Sales Price"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "discount_percent",
			"label": _("Discount %"),
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"fieldname": "reseller_item",
			"label": _("Reseller Item"),
			"fieldtype": "Check",
			"width": 100
		},
		{
			"fieldname": "selling_stop",
			"label": _("Selling Stop"),
			"fieldtype": "Check",
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

	# Enrich data with price information
	data = []
	for item in items:
		item_data = item.copy()

		# Get prices using settings
		purchase_price = get_item_price(item.item_code, settings["purchase"])
		reseller_price = get_item_price(item.item_code, settings["reseller"])
		gross_sales_price = get_item_price(item.item_code, settings["gross_sales"])
		net_sales_price = get_item_price(item.item_code, settings["net_sales"])

		item_data["purchase_price"] = purchase_price
		item_data["reseller_price"] = reseller_price
		item_data["gross_sales_price"] = gross_sales_price

		# Calculate discount percentage
		if reseller_price and net_sales_price and net_sales_price > 0:
			item_data["discount_percent"] = ((net_sales_price - reseller_price) / net_sales_price) * 100
		else:
			item_data["discount_percent"] = 0

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
		.select(ItemSupplier.supplier)
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