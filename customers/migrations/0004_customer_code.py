from django.db import migrations, models


def vendor_prefix(name):
    n = (name or "").strip()
    if not n:
        return "XX"
    first, last = n[0].upper(), n[-1].upper()
    if not first.isalnum():
        first = "X"
    if not last.isalnum():
        last = "X"
    return (first + last)[:2]


def backfill_customer_codes(apps, schema_editor):
    Customer = apps.get_model("customers", "Customer")
    Vendor = apps.get_model("vendors", "Vendor")

    for vendor in Vendor.objects.all():
        for c in Customer.objects.filter(vendor=vendor).order_by("id"):
            if c.customer_code:
                continue
            prefix = vendor_prefix(vendor.name)
            suffix_num = c.id
            code = f"{prefix}{suffix_num:02d}"[:10]
            step = 0
            while Customer.objects.filter(vendor_id=vendor.id, customer_code=code).exclude(pk=c.pk).exists():
                step += 1
                code = f"{prefix}{suffix_num:02d}{step}"[:10]
            Customer.objects.filter(pk=c.pk).update(customer_code=code)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0003_loan_day_cycle"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="customer_code",
            field=models.CharField(max_length=10, editable=False, null=True),
        ),
        migrations.RunPython(backfill_customer_codes, noop),
        migrations.AlterField(
            model_name="customer",
            name="customer_code",
            field=models.CharField(max_length=10, editable=False),
        ),
        migrations.AddIndex(
            model_name="customer",
            index=models.Index(fields=["vendor", "customer_code"], name="idx_customer_vendor_code"),
        ),
        migrations.AddConstraint(
            model_name="customer",
            constraint=models.UniqueConstraint(
                fields=("vendor", "customer_code"),
                name="uniq_customer_vendor_code",
            ),
        ),
    ]
