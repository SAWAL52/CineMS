
from django.db import migrations, models
import django.db.models.deletion


def migrate_cinema_data(apps, schema_editor):
    """
    Preserve existing cinema locations on CinemaHall records,
    then merge duplicate cinema brands while keeping their halls.
    """
    db_alias = schema_editor.connection.alias

    Cinema = apps.get_model("core", "Cinema")
    CinemaHall = apps.get_model("core", "CinemaHall")

    # Step 1: Copy each old Cinema location to its halls.
    for cinema in Cinema.objects.using(db_alias).order_by("pk"):
        old_location = cinema.location or ""

        CinemaHall.objects.using(db_alias).filter(
            cinema_id=cinema.pk,
            location="",
        ).update(location=old_location)

    # Step 2: Merge duplicate brands.
    # Keep the lowest primary key for each brand name.
    seen_brands = {}

    for cinema in Cinema.objects.using(db_alias).order_by("pk"):
        if cinema.name not in seen_brands:
            seen_brands[cinema.name] = cinema.pk
            continue

        keeper_id = seen_brands[cinema.name]

        # Reassign halls before deleting the duplicate brand.
        CinemaHall.objects.using(db_alias).filter(
            cinema_id=cinema.pk,
        ).update(cinema_id=keeper_id)

        cinema.delete(using=db_alias)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_cinemahallauditorium"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="cinemahallauditorium",
            options={},
        ),

        migrations.AlterUniqueTogether(
            name="cinemahallauditorium",
            unique_together=set(),
        ),

        # Add the new location field before copying existing data.
        migrations.AddField(
            model_name="cinemahall",
            name="location",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
            ),
        ),

        # Copy locations and merge duplicate Cinema records.
        migrations.RunPython(
            migrate_cinema_data,
            reverse_code=migrations.RunPython.noop,
        ),

        # Remove the old location field only after copying its data.
        migrations.RemoveField(
            model_name="cinema",
            name="location",
        ),

        # Brand names must now be unique.
        migrations.AlterField(
            model_name="cinema",
            name="name",
            field=models.CharField(
                max_length=100,
                unique=True,
            ),
        ),

        # Retain the existing nullable relationship.
        migrations.AlterField(
            model_name="cinemahall",
            name="cinema",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="halls",
                to="core.cinema",
            ),
        ),

        # Prevent duplicate auditorium names within the same hall.
        migrations.AddConstraint(
            model_name="cinemahallauditorium",
            constraint=models.UniqueConstraint(
                fields=("cinemahall", "name"),
                name="unique_auditorium_name_per_hall",
            ),
        ),
    ]
