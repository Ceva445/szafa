import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import (
    Company,
    Department,
    Position,
    Supplier,
    ProductCategory,
    Product,
)
from employees.models import Employee
from warehouse.models import WarehouseStock


class Command(BaseCommand):
    help = "Import data from Obłsuga magazynu.xlsm into database"

    def add_arguments(self, parser):
        parser.add_argument("xlsm_path", type=str, help="Path to the .xlsm file")

    @transaction.atomic
    def handle(self, *args, **options):
        path = options["xlsm_path"]
        self.stdout.write(self.style.WARNING(f"📂 Importing data from {path} ..."))
        xls = pd.ExcelFile(path)

        # --- 1️⃣ Positions ---
        if "Position" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="Position")
            df = df.iloc[:, 0].dropna().drop_duplicates()
            for name in df:
                Position.objects.get_or_create(name=str(name).strip())
            self.stdout.write(self.style.SUCCESS(f"✅ Imported {len(df)} positions."))

        # --- 2️⃣ Departments ---
        if "Department" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="Department")
            df = df.iloc[:, 0].dropna().drop_duplicates()
            for name in df:
                Department.objects.get_or_create(name=str(name).strip())
            self.stdout.write(self.style.SUCCESS(f"✅ Imported {len(df)} departments."))

        # --- 3️⃣ Suppliers ---
        if "Supplier" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="Supplier")
            df = df.iloc[:, 0].dropna().drop_duplicates()
            for name in df:
                Supplier.objects.get_or_create(name=str(name).strip())
            self.stdout.write(self.style.SUCCESS(f"✅ Imported {len(df)} suppliers."))

        # --- 4️⃣ Product Categories ---
        if "Productcategory" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="Productcategory")
            df = df.iloc[:, 0].dropna().drop_duplicates()

            def map_type(name):
                name = str(name).lower()
                if "odzież" in name:
                    return "clothing"
                elif "obuw" in name:
                    return "footwear"
                elif "bhp" in name:
                    return "bhp"
                return "clothing"

            for name in df:
                ProductCategory.objects.get_or_create(
                    name=str(name).strip(),
                    type=map_type(name),
                )
            self.stdout.write(
                self.style.SUCCESS(f"✅ Imported {len(df)} product categories.")
            )

        # --- 5️⃣ Companies (from employees sheet) ---
        if "Lista pracowników" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="Lista pracowników")
            if "Firma" in df.columns:
                companies = df["Firma"].dropna().unique()
                for name in companies:
                    Company.objects.get_or_create(name=str(name).strip())
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Imported {len(companies)} companies.")
                )

        # --- 6️⃣ Products ---
        if "Procuct" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="Procuct")
            for _, row in df.iterrows():
                category_name = str(row.get("Category", "")).strip()
                category_obj, _ = ProductCategory.objects.get_or_create(
                    name=category_name or "Nieznana",
                    type="clothing",
                )
                Product.objects.get_or_create(
                    code=str(row["Code"]).strip(),
                    defaults={
                        "name": str(row.get("Name", "")).strip(),
                        "category": category_obj,
                        "size": (
                            str(row.get("Size"))
                            if not pd.isna(row.get("Size"))
                            else None
                        ),
                        "unit_price": float(row.get("Unit price", 0)),
                        "period_days": int(row.get("Period days", 0)),
                        "min_qty_on_stock": int(row.get("Min qty on stock", 0)),
                        "description": str(row.get("Description", "")),
                    },
                )
            self.stdout.write(self.style.SUCCESS(f"✅ Imported {len(df)} products."))

        # --- 7️⃣ Employees ---
        if "Lista pracowników" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="Lista pracowników")
            for _, row in df.iterrows():
                company, _ = Company.objects.get_or_create(
                    name=str(row["Firma"]).strip()
                )
                department, _ = Department.objects.get_or_create(
                    name=str(row["DZIAŁ"]).strip()
                )
                position, _ = Position.objects.get_or_create(
                    name=str(row["Stanowisko"]).strip()
                )

                Employee.objects.get_or_create(
                    card_number=str(row["Kod pracownika"]).strip(),
                    defaults={
                        "first_name": str(row["Imię"]).strip(),
                        "last_name": str(row["Nazwisko"]).strip(),
                        "company": company,
                        "department": department,
                        "position": position,
                    },
                )
            self.stdout.write(self.style.SUCCESS(f"✅ Imported {len(df)} employees."))

        # --- 8️⃣ Warehouse Stock ---
        if "aktualny stan magazynu " in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="aktualny stan magazynu ")
            for _, row in df.iterrows():
                product_code = str(row["indeks"]).strip()
                size = (
                    str(row["rozmiar"]).strip() if not pd.isna(row["rozmiar"]) else None
                )
                quantity = int(row["ilość"]) if not pd.isna(row["ilość"]) else 0
                product = Product.objects.filter(code=product_code).first()
                if product:
                    WarehouseStock.objects.update_or_create(
                        product=product,
                        size=size,
                        defaults={"quantity": quantity},
                    )
            self.stdout.write(self.style.SUCCESS(f"✅ Imported warehouse stock data."))

        self.stdout.write(self.style.SUCCESS("🎉 Import completed successfully!"))
