from django.db import migrations

def seed_roles(apps, schema_editor):
    Rol = apps.get_model('authz', 'Rol')
    for nombre in ["ADMIN", "AGENTE", "CLIENTE"]:
        Rol.objects.get_or_create(nombre=nombre)

def noop(apps, schema_editor):
    # No eliminamos roles en reversa para evitar pérdida de datos
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('authz', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_roles, noop),
    ]
