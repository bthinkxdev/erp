from django.db import migrations, models


def backfill_vendor_whatsapp(apps, schema_editor):
    Vendor = apps.get_model("vendors", "Vendor")
    Vendor.objects.filter(whatsapp_number__isnull=True).update(whatsapp_number="0000000000")


class Migration(migrations.Migration):

    dependencies = [
        ("vendors", "0002_vendor_staff_customer_scope"),
    ]

    operations = [
        migrations.AddField(
            model_name="vendor",
            name="whatsapp_number",
            field=models.CharField(
                db_index=True,
                help_text="Business WhatsApp number (digits; include country code without +, e.g. 919876543210).",
                max_length=32,
                null=True,
                verbose_name="WhatsApp number",
            ),
        ),
        migrations.RunPython(backfill_vendor_whatsapp, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="vendor",
            name="whatsapp_number",
            field=models.CharField(
                db_index=True,
                help_text="Business WhatsApp number (digits; include country code without +, e.g. 919876543210).",
                max_length=32,
                verbose_name="WhatsApp number",
            ),
        ),
    ]
