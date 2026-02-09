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
	],

	onload: function(report) {
		// Define update functions globally
		window.update_reseller_price = function(item_code, price_list_name, new_price) {
			frappe.call({
				method: "suppliercatalog.german_accounting.report.reseller_price_list.reseller_price_list.update_item_price",
				args: {
					item_code: item_code,
					price_list_name: price_list_name,
					new_price: new_price
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						// Show link to updated document
						let link = `<a href='/app/${r.message.doctype.toLowerCase().replace(/ /g, '-')}/${encodeURIComponent(r.message.doc_name)}' target='_blank'>${r.message.doc_name}</a>`;
						frappe.msgprint({
							title: __(r.message.action === 'created' ? 'Created' : 'Updated'),
							message: __("<strong>Field:</strong> Reseller Price<br><strong>Value:</strong> {0}<br><strong>Item:</strong> {1}<br><strong>Document:</strong> {2}", [
								new_price,
								item_code,
								link
							]),
							indicator: 'green'
						});
						// Recalculate discount percentage
						report.refresh();
					}
				}
			});
		};

		window.update_gross_sales_price = function(item_code, price_list_name, new_price) {
			frappe.call({
				method: "suppliercatalog.german_accounting.report.reseller_price_list.reseller_price_list.update_item_price",
				args: {
					item_code: item_code,
					price_list_name: price_list_name,
					new_price: new_price
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						// Show link to updated document
						let link = `<a href='/app/${r.message.doctype.toLowerCase().replace(/ /g, '-')}/${encodeURIComponent(r.message.doc_name)}' target='_blank'>${r.message.doc_name}</a>`;
						frappe.msgprint({
							title: __(r.message.action === 'created' ? 'Created' : 'Updated'),
							message: __("<strong>Field:</strong> Gross Sales Price<br><strong>Value:</strong> {0}<br><strong>Item:</strong> {1}<br><strong>Document:</strong> {2}", [
								new_price,
								item_code,
								link
							]),
							indicator: 'green'
						});
						report.refresh();
					}
				}
			});
		};

		window.update_discount_percent = function(item_code, discount_percent) {
			frappe.call({
				method: "suppliercatalog.german_accounting.report.reseller_price_list.reseller_price_list.update_reseller_price_by_discount",
				args: {
					item_code: item_code,
					discount_percent: discount_percent
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						// Update the reseller price input field
						$(`#reseller_price_${item_code}`).val(r.message.new_reseller_price.toFixed(2));
						// Show link to updated document with price info
						let link = `<a href='/app/${r.message.doctype.toLowerCase().replace(/ /g, '-')}/${encodeURIComponent(r.message.doc_name)}' target='_blank'>${r.message.doc_name}</a>`;
						frappe.msgprint({
							title: __(r.message.action === 'created' ? 'Created' : 'Updated'),
							message: __("<strong>Field:</strong> Discount %<br><strong>Value:</strong> {0}%<br><strong>Calculated Reseller Price:</strong> {1}<br><strong>Item:</strong> {2}<br><strong>Document:</strong> {3}", [
								discount_percent,
								r.message.new_reseller_price.toFixed(2),
								item_code,
								link
							]),
							indicator: 'green'
						});
					}
				}
			});
		};

		window.update_item_field = function(item_code, field_name, value) {
			let field_label = field_name === 'custom_reseller_item' ? 'Reseller Item' : 'Selling Stop';
			let value_label = value ? 'Checked' : 'Unchecked';
			
			frappe.call({
				method: "suppliercatalog.german_accounting.report.reseller_price_list.reseller_price_list.update_item_field",
				args: {
					item_code: item_code,
					field_name: field_name,
					value: value
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						// Show link to updated document
						let link = `<a href='/app/${r.message.doctype.toLowerCase().replace(/ /g, '-')}/${encodeURIComponent(r.message.doc_name)}' target='_blank'>${r.message.doc_name}</a>`;
						frappe.msgprint({
							title: __('Updated'),
							message: __("<strong>Field:</strong> {0}<br><strong>Value:</strong> {1}<br><strong>Document:</strong> {2}", [
								field_label,
								value_label,
								link
							]),
							indicator: 'green'
						});
					}
				}
			});
		};
	}
};
