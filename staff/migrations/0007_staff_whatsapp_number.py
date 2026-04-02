from django.db import migrations, models


def backfill_staff_whatsapp(apps, schema_editor):
    Staff = apps.get_model("staff", "Staff")
    Staff.objects.filter(phone="").update(phone="0000000000")


class Migration(migrations.Migration):

    dependencies = [
        ("staff", "0006_split_customer_permissions"),
    ]

    operations = [
        migrations.RunPython(backfill_staff_whatsapp, migrations.RunPython.noop),
        migrations.RenameField(
            model_name="staff",
            old_name="phone",
            new_name="whatsapp_number",
        ),
        migrations.AlterField(
            model_name="staff",
            name="whatsapp_number",
            field=models.CharField(
                db_index=True,
                help_text="WhatsApp number for this team member (digits; include country code without +).",
                max_length=32,
                verbose_name="WhatsApp number",
            ),
        ),
    ]
