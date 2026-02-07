import frappe
import csv
import io
import re
from frappe.utils import now_datetime
from charset_normalizer import from_bytes

UNIT_MAPPING = {
    "1 kg": "kg",
    "1 l": "Liter",
    "L" : "Liter",
}

def normalize_unit(value: str | None) -> str | None:
    if not value:
        return None

    value = value.strip()

    return UNIT_MAPPING.get(value, value)



def _get_raw(row, idx):
    """
    Return a stripped string value from a CSV row by index.
    If index is out of bounds or value is None => empty string.
    """
    if idx < 0 or idx >= len(row):
        return ""
    value = row[idx]
    return str(value).strip() if value is not None else ""


def _clean_number_db(value):
    """
    Clean numeric values for database insertion.

    - Replace comma with dot for decimal
    - Remove leading zeros
    - '01,5' -> '1.5'
    - '00,05' -> '0.05'
    - '' / '0' / '000' / '0,00' -> ''
    """
    if not value:
        return ""

    # Replace comma with dot for ERPNext float/currency
    value = value.strip().replace(",", ".")

    try:
        number = float(value)
        # Treat zero as empty
        return "" if number == 0 else number
    except ValueError:
        return ""


def _set_if_value(payload, fieldname, value, clean_number_db=False):
    """
    Set payload[fieldname] if value is not empty.
    Optionally apply float cleanup for DB (price/number fields).
    """
    if clean_number_db:
        value = _clean_number_db(value)
    if value != "":
        payload[fieldname] = value


def _set_checkbox(payload, fieldname, value):
    """
    Convert J/N values to ERPNext checkbox (1/0).
    J => 1
    N => 0
    Otherwise skip
    """
    v = value.upper()
    if v == "J":
        payload[fieldname] = 1
    elif v == "N":
        payload[fieldname] = 0


def import_supplier_catalog_items_from_csv(doc):
    """
    Import Supplier Catalog Items from a BNN-style CSV attached to a Supplier Catalog.
    Synchronous import with a single GUI progress bar.
    """

    BATCH_SIZE = 200
    PROGRESS_EVERY = 25

    processed = 0
    imported = 0

    # -------------------------------------------------
    # Load CSV
    # -------------------------------------------------
    file_doc = frappe.get_doc("File", {"file_url": doc.import_file})
    file_path = file_doc.get_full_path()

    with open(file_path, "rb") as f:
        raw = f.read()

    
    matches = from_bytes(raw)

    if not matches or matches.best() is None:
        raise frappe.ValidationError(
            "Could not detect CSV encoding automatically."
        )

    best = matches.best()
    encoding_used = best.encoding

    # decode safely
    text = str(best)

    frappe.logger().info(
        f"Supplier Catalog CSV detected encoding: {encoding_used}"
    )

   
    reader = csv.reader(io.StringIO(text), delimiter=";", quotechar='"')
    lines = list(reader)

    if len(lines) < 2:
        frappe.throw("The file must contain at least a header and one data row.")

    if _get_raw(lines[0], 0) != "BNN":
        frappe.throw("No BNN file detected. Please upload a valid BNN CSV file.")

    # -------------------------------------------------
    # Preload mappings
    # -------------------------------------------------
    country_map = {
        c.code.lower(): c.name
        for c in frappe.get_all("Country", fields=["name", "code"])
        if c.code
    }

    brand_map = {
        b.abbreviation.upper(): b.name
        for b in frappe.get_all("Supplier Catalog Brand", fields=["name", "abbreviation"])
        if b.abbreviation
    }

    quality_map = {
        q.abbreviation_data.upper(): q.name
        for q in frappe.get_all("Supplier Quality", fields=["name", "abbreviation_data"])
        if q.abbreviation_data
    }

    tradeclass_names = {
        t.name for t in frappe.get_all("Trade Class", fields=["name"])
    }

    file_age_val = _get_raw(lines[0], 9)
    if file_age_val:
        try:
            doc.db_set("file_age", file_age_val)
        except Exception:
            pass

    total_rows = len(lines) - 2
    now_dt = now_datetime()

    # -------------------------------------------------
    # Import rows
    # -------------------------------------------------
    for index, row in enumerate(lines[1:-1], start=1):

        payload = {"doctype": "Supplier Catalog Item"}
        base_len = len(payload)

        _set_if_value(payload, "supplier_itemnumber", _get_raw(row, 0))

        imported_date = _get_raw(row, 2)
        imported_time = _get_raw(row, 3)

        payload["last_imported"] = imported_date if imported_date else now_dt.date()
        payload["last_imported_time"] = imported_time if imported_time else now_dt.time()

        _set_if_value(payload, "ean_shop", _get_raw(row, 4))
        _set_if_value(payload, "ean_order", _get_raw(row, 5))
        _set_if_value(payload, "name1", _get_raw(row, 6))
        _set_if_value(payload, "name2", _get_raw(row, 7))

        tradeclass = _get_raw(row, 9)
        if tradeclass in tradeclass_names:
            payload["tradeclass"] = tradeclass

        brand_code = _get_raw(row, 10).upper()
        if brand_code in brand_map:
            payload["brand"] = brand_map[brand_code]

        iso2 = _get_raw(row, 12).lower()
        if iso2 in country_map:
            payload["country_of_origin"] = country_map[iso2]

        quality_code = _get_raw(row, 13).upper()
        if quality_code in quality_map:
            payload["supplierquality"] = quality_map[quality_code]

        _set_if_value(payload, "controlagency", _get_raw(row, 14))
        _set_if_value(payload, "remaining_shelf_life", _get_raw(row, 15), clean_number_db=True)
        _set_if_value(payload, "orderunit_quantity", _get_raw(row, 22), clean_number_db=True)
        _set_if_value(payload, "shop_unit", _get_raw(row, 23))

        _set_checkbox(payload, "weight_item", _get_raw(row, 25))

        _set_if_value(payload, "weight_shop_unit", _get_raw(row, 28), clean_number_db=True)
        _set_if_value(payload, "weight_order_unit", _get_raw(row, 29), clean_number_db=True)
        _set_if_value(payload, "width", _get_raw(row, 30), clean_number_db=True)
        _set_if_value(payload, "height", _get_raw(row, 31), clean_number_db=True)
        _set_if_value(payload, "depth", _get_raw(row, 32), clean_number_db=True)

        tax_code = _get_raw(row, 33)
        if tax_code == "1":
            payload["tax_amount"] = 7
        elif tax_code == "2":
            payload["tax_amount"] = 19
        elif tax_code == "3":
            payload["tax_amount"] = 9

        _set_if_value(payload, "recommended_sales_price", _get_raw(row, 35), clean_number_db=True)
        _set_if_value(payload, "ek_price", _get_raw(row, 37), clean_number_db=True)

        _set_if_value(payload, "base_price_unit", normalize_unit(_get_raw(row, 65)))
        _set_if_value(payload, "base_price_faktor", _get_raw(row, 66), clean_number_db=True)
        _set_if_value(payload, "item_bio_id", _get_raw(row, 69))

        payload["supplier_catalog"] = doc.name
        payload["supplier"] = doc.supplier

        if len(payload) > base_len + 2:

            existing_name = frappe.db.get_value(
                "Supplier Catalog Item",
                {
                    "supplier": doc.supplier,
                    "supplier_itemnumber": payload.get("supplier_itemnumber")
                },
                "name"
            )

            if existing_name:
                doc_item = frappe.get_doc("Supplier Catalog Item", existing_name)
                for field, value in payload.items():
                    if field in ("doctype", "supplier", "supplier_catalog"):
                        continue
                    if value not in (None, ""):
                        doc_item.set(field, value)

                doc_item.flags.ignore_mandatory = True
                doc_item.save(ignore_permissions=True)

            else:
                doc_item = frappe.get_doc(payload)
                doc_item.flags.ignore_mandatory = True
                doc_item.insert(ignore_permissions=True)
                imported += 1

        processed += 1

        # ---- batch commit ----
        if processed % BATCH_SIZE == 0:
            frappe.db.commit()
            frappe.db.begin()

        # ---- throttled progress ----
        if index % PROGRESS_EVERY == 0 or index == total_rows:
            frappe.publish_progress(
                int((index / total_rows) * 100),
                title="Supplier Catalog Import",
                description=f"Processed {index} of {total_rows}"
            )

    frappe.db.commit()

    doc.db_set("import_status", "Success")
    doc.db_set("import_amount", imported)
    doc.db_set("last_imported", now_datetime())

    frappe.publish_progress(
        100,
        title="Supplier Catalog Import",
        description=f"Finished. Imported {imported} items."
    )

    frappe.publish_realtime(
        "msgprint",
        {
            "message": (
                f"Product import finished.<br>"
                f"Imported: {imported}<br>"
            )
        },
        user=frappe.session.user
    )

    return f"{imported} items imported successfully."