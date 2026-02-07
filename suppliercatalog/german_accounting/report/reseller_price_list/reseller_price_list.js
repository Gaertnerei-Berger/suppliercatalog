frappe.query_reports["Reseller Price List"] = {
	"filters": [
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
		},
		{
			"fieldname": "supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"get_query": function() {
				return {
					"query": "suppliercatalog.german_accounting.report.reseller_price_list.reseller_price_list.get_suppliers_from_items"
				};
			}
		},
		{
			"fieldname": "reseller_item",
			"label": __("Reseller Item"),
			"fieldtype": "Check"
		},
		{
			"fieldname": "selling_stop",
			"label": __("Selling Stop"),
			"fieldtype": "Check"
		}
	]
};