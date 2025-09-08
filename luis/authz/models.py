from django.db import models
from core.models import TimeStampedModel

class Rol(TimeStampedModel):
    nombre = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nombre

class Usuario(TimeStampedModel):
    ESTADOS = (("ACTIVO","ACTIVO"),("INACTIVO","INACTIVO"),("BLOQUEADO","BLOQUEADO"))
    nombre = models.CharField(max_length=100)
    email = models.EmailField(max_length=191, unique=True)
    password_hash = models.CharField(max_length=255)
    telefono = models.CharField(max_length=25, blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="ACTIVO")
    roles = models.ManyToManyField(Rol, through="RolUsuario", related_name="usuarios")
    def __str__(self): return f"{self.nombre} <{self.email}>"

class RolUsuario(models.Model):
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    class Meta:
        unique_together = (("rol","usuario"),)
