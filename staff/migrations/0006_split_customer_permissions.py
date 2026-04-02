from django.db import migrations, models


def forwards_copy_flags(apps, schema_editor):
    Staff = apps.get_model("staff", "Staff")
    for row in Staff.objects.all():
        if row.can_manage_customers:
            Staff.objects.filter(pk=row.pk).update(
                can_add_customers=True,
                can_edit_customers=True,
            )


def backwards_merge_flags(apps, schema_editor):
    Staff = apps.get_model("staff", "Staff")
    for row in Staff.objects.all():
        merged = row.can_add_customers or row.can_edit_customers
        Staff.objects.filter(pk=row.pk).update(can_manage_customers=merged)


class Migration(migrations.Migration):

    dependencies = [
        ("staff", "0005_staff_can_manage_customers"),
    ]

    operations = [
        migrations.AddField(
            model_name="staff",
            name="can_add_customers",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Create new customers (subject to customer visibility rules for this vendor).",
            ),
        ),
        migrations.AddField(
            model_name="staff",
            name="can_edit_customers",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Edit existing customers (subject to customer visibility rules for this vendor).",
            ),
        ),
        migrations.RunPython(forwards_copy_flags, backwards_merge_flags),
        migrations.RemoveField(
            model_name="staff",
            name="can_manage_customers",
        ),
    ]
