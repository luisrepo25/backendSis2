from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Reserva, Visitante, ReservaServicio, ReservaVisitante
from .services import ReservaService, CotizacionService, DisponibilidadService
from authz.models import Usuario, Rol
from catalogo.models import Categoria, Servicio
from cupones.models import Cupon

User = get_user_model()

class ReservaModelTest(TestCase):
    def setUp(self):
        # Crear usuario
        self.django_user = User.objects.create_user(
            username='testuser',
            email='test@example.com', 
            password='testpass123'
        )
        
        self.usuario = Usuario.objects.create(
            nombre="Test User",
            email="test@example.com",
            password_hash="hashed",
            telefono="123456789"
        )
        
        # Crear categoría y servicio
        self.categoria = Categoria.objects.create(
            nombre="Tours",
            descripcion="Tours turísticos"
        )
        
        self.servicio = Servicio.objects.create(
            tipo="TOUR",
            titulo="City Tour",
            descripcion="Tour por la ciudad",
            duracion_min=120,
            costo=Decimal("100.00"),
            capacidad_max=20,
            punto_encuentro="Plaza Principal",
            categoria=self.categoria
        )
        
        # Crear cupón
        self.cupon = Cupon.objects.create(
            codigo="TEST20",
            tipo="PORCENTAJE",
            valor=Decimal("20.00"),
            estado=True
        )
        
        # Crear reserva
        self.reserva = Reserva.objects.create(
            usuario=self.usuario,
            fecha_inicio=timezone.now() + timedelta(days=1),
            total=Decimal("100.00")
        )
        
        # Crear detalle de reserva
        ReservaServicio.objects.create(
            reserva=self.reserva,
            servicio=self.servicio,
            cantidad=1,
            precio_unitario=self.servicio.costo
        )

    def test_calcular_total_sin_descuento(self):
        """Test cálculo de total base"""
        total = self.reserva.calcular_total_sin_descuento()
        self.assertEqual(total, Decimal("100.00"))

    def test_aplicar_cupon_valido(self):
        """Test aplicación de cupón válido"""
        success, mensaje = self.reserva.aplicar_cupon("TEST20")
        self.assertTrue(success)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.total, Decimal("80.00"))  # 100 - 20%

    def test_aplicar_cupon_inexistente(self):
        """Test aplicación de cupón inexistente"""
        success, mensaje = self.reserva.aplicar_cupon("NOEXISTE")
        self.assertFalse(success)
        self.assertIn("no encontrado", mensaje.lower())

    def test_cancelar_reserva_valida(self):
        """Test cancelación de reserva pendiente"""
        success, mensaje = self.reserva.cancelar()
        self.assertTrue(success)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "CANCELADA")

    def test_confirmar_pago(self):
        """Test confirmación de pago"""
        success, mensaje = self.reserva.confirmar_pago()
        self.assertTrue(success)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "PAGADA")

    def test_no_cancelar_reserva_pagada(self):
        """Test que no se puede cancelar reserva pagada"""
        self.reserva.estado = "PAGADA"
        self.reserva.save()
        
        success, mensaje = self.reserva.cancelar()
        self.assertFalse(success)


class ServicioModelTest(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(
            nombre="Tours",
            descripcion="Tours turísticos"
        )
        
        self.servicio = Servicio.objects.create(
            tipo="TOUR",
            titulo="City Tour",
            descripcion="Tour por la ciudad",
            duracion_min=150,
            costo=Decimal("100.00"),
            capacidad_max=20,
            punto_encuentro="Plaza Principal",
            categoria=self.categoria
        )

    def test_disponibilidad_basica(self):
        """Test verificación de disponibilidad básica"""
        fecha_futura = timezone.now().date() + timedelta(days=1)
        disponible, mensaje = self.servicio.esta_disponible(fecha_futura, 5)
        self.assertTrue(disponible)

    def test_no_disponible_fecha_pasada(self):
        """Test que no esté disponible para fechas pasadas"""
        fecha_pasada = timezone.now().date() - timedelta(days=1)
        disponible, mensaje = self.servicio.esta_disponible(fecha_pasada, 5)
        self.assertFalse(disponible)

    def test_capacidad_excedida(self):
        """Test capacidad máxima excedida"""
        fecha_futura = timezone.now().date() + timedelta(days=1)
        disponible, mensaje = self.servicio.esta_disponible(fecha_futura, 25)
        self.assertFalse(disponible)
        self.assertIn("capacidad", mensaje.lower())

    def test_duracion_formateada(self):
        """Test formato de duración"""
        duracion = self.servicio.get_duracion_formateada()
        self.assertEqual(duracion, "2h 30min")

    def test_precio_formateado(self):
        """Test formato de precio"""
        precio = self.servicio.precio_formateado
        self.assertEqual(precio, "Bs. 100.00")


class ReservaServiceTest(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create(
            nombre="Test User",
            email="test@example.com",
            password_hash="hashed",
            telefono="123456789"
        )
        
        self.categoria = Categoria.objects.create(
            nombre="Tours",
            descripcion="Tours turísticos"
        )
        
        self.servicio = Servicio.objects.create(
            tipo="TOUR",
            titulo="City Tour",
            duracion_min=120,
            costo=Decimal("100.00"),
            capacidad_max=20,
            punto_encuentro="Plaza Principal",
            categoria=self.categoria
        )

    def test_crear_reserva_completa_exitosa(self):
        """Test creación exitosa de reserva completa"""
        servicios_data = [{
            'servicio_id': self.servicio.id,
            'cantidad': 2,
            'fecha_servicio': timezone.now() + timedelta(days=1)
        }]
        
        visitantes_data = [{
            'documento': '12345678',
            'nombre': 'Juan',
            'apellido': 'Pérez',
            'fecha_nacimiento': '1990-01-01',
            'email': 'juan@example.com'
        }]
        
        success, mensaje, reserva = ReservaService.crear_reserva_completa(
            usuario=self.usuario,
            servicios_data=servicios_data,
            visitantes_data=visitantes_data,
            fecha_inicio=timezone.now() + timedelta(days=1)
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(reserva)
        self.assertEqual(reserva.total, Decimal("200.00"))  # 2 servicios de 100 c/u

    def test_crear_reserva_servicio_inexistente(self):
        """Test error con servicio inexistente"""
        servicios_data = [{
            'servicio_id': 99999,  # ID inexistente
            'cantidad': 1
        }]
        
        visitantes_data = [{
            'documento': '12345678',
            'nombre': 'Juan',
            'apellido': 'Pérez',
            'fecha_nacimiento': '1990-01-01'
        }]
        
        success, mensaje, reserva = ReservaService.crear_reserva_completa(
            usuario=self.usuario,
            servicios_data=servicios_data,
            visitantes_data=visitantes_data,
            fecha_inicio=timezone.now() + timedelta(days=1)
        )
        
        self.assertFalse(success)
        self.assertIsNone(reserva)
        self.assertIn("no existen", mensaje.lower())


class CotizacionServiceTest(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(
            nombre="Tours",
            descripcion="Tours turísticos"
        )
        
        self.servicio = Servicio.objects.create(
            tipo="TOUR",
            titulo="City Tour",
            duracion_min=120,
            costo=Decimal("100.00"),
            capacidad_max=20,
            punto_encuentro="Plaza Principal",
            categoria=self.categoria
        )
        
        self.cupon = Cupon.objects.create(
            codigo="DESC20",
            tipo="PORCENTAJE",
            valor=Decimal("20.00"),
            estado=True
        )

    def test_generar_cotizacion_sin_cupon(self):
        """Test generación de cotización sin cupón"""
        servicios_data = [{
            'servicio_id': self.servicio.id,
            'cantidad': 2
        }]
        
        cotizacion = CotizacionService.generar_cotizacion(servicios_data)
        
        self.assertEqual(cotizacion['subtotal'], Decimal("200.00"))
        self.assertEqual(cotizacion['descuento'], Decimal("0.00"))
        self.assertEqual(cotizacion['total'], Decimal("200.00"))
        self.assertFalse(cotizacion['cupon_valido'])

    def test_generar_cotizacion_con_cupon(self):
        """Test generación de cotización con cupón válido"""
        servicios_data = [{
            'servicio_id': self.servicio.id,
            'cantidad': 2
        }]
        
        cotizacion = CotizacionService.generar_cotizacion(servicios_data, "DESC20")
        
        self.assertEqual(cotizacion['subtotal'], Decimal("200.00"))
        self.assertEqual(cotizacion['descuento'], Decimal("40.00"))  # 20% de 200
        self.assertEqual(cotizacion['total'], Decimal("160.00"))
        self.assertTrue(cotizacion['cupon_valido'])


class DisponibilidadServiceTest(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(
            nombre="Tours",
            descripcion="Tours turísticos"
        )
        
        self.servicio1 = Servicio.objects.create(
            tipo="TOUR",
            titulo="City Tour",
            duracion_min=120,
            costo=Decimal("100.00"),
            capacidad_max=20,
            punto_encuentro="Plaza Principal",
            categoria=self.categoria
        )
        
        self.servicio2 = Servicio.objects.create(
            tipo="ACTIVIDAD",
            titulo="Hiking",
            duracion_min=240,
            costo=Decimal("150.00"),
            capacidad_max=10,
            punto_encuentro="Entrada del parque",
            categoria=self.categoria
        )

    def test_verificar_disponibilidad_multiple(self):
        """Test verificación de disponibilidad de múltiples servicios"""
        servicios_ids = [self.servicio1.id, self.servicio2.id]
        fecha = timezone.now() + timedelta(days=1)
        
        resultado = DisponibilidadService.verificar_disponibilidad_multiple(
            servicios_ids, fecha, 5
        )
        
        self.assertIn(self.servicio1.id, resultado)
        self.assertIn(self.servicio2.id, resultado)
        self.assertTrue(resultado[self.servicio1.id]['disponible'])
        self.assertTrue(resultado[self.servicio2.id]['disponible'])
