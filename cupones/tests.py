from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from .models import Cupon
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()

class CuponModelTest(TestCase):
    def setUp(self):
        self.cupon_porcentaje = Cupon.objects.create(
            codigo="DESC20",
            tipo="PORCENTAJE",
            valor=Decimal("20.00"),
            fecha_inicio=timezone.now() - timedelta(days=1),
            fecha_fin=timezone.now() + timedelta(days=30),
            estado=True
        )
        
        self.cupon_fijo = Cupon.objects.create(
            codigo="FIJO50",
            tipo="FIJO",
            valor=Decimal("50.00"),
            estado=True
        )

    def test_cupon_porcentaje_calculo(self):
        """Test cálculo de descuento por porcentaje"""
        total = Decimal("100.00")
        descuento = self.cupon_porcentaje.calcular_descuento(total)
        self.assertEqual(descuento, Decimal("20.00"))

    def test_cupon_fijo_calculo(self):
        """Test cálculo de descuento fijo"""
        total = Decimal("100.00")
        descuento = self.cupon_fijo.calcular_descuento(total)
        self.assertEqual(descuento, Decimal("50.00"))

    def test_cupon_fijo_mayor_que_total(self):
        """Test que descuento fijo no exceda el total"""
        total = Decimal("30.00")
        descuento = self.cupon_fijo.calcular_descuento(total)
        self.assertEqual(descuento, Decimal("30.00"))

    def test_cupon_expirado(self):
        """Test validación de cupón expirado"""
        cupon_expirado = Cupon.objects.create(
            codigo="EXPIRADO",
            tipo="FIJO", 
            valor=Decimal("10.00"),
            fecha_fin=timezone.now() - timedelta(days=1),
            estado=True
        )
        
        es_valido, mensaje = cupon_expirado.es_valido()
        self.assertFalse(es_valido)
        self.assertIn("expirado", mensaje.lower())

    def test_validar_codigo_existente(self):
        """Test validación de código existente"""
        cupon, mensaje = Cupon.validar_codigo("DESC20")
        self.assertIsNotNone(cupon)
        self.assertEqual(cupon.codigo, "DESC20")

    def test_validar_codigo_inexistente(self):
        """Test validación de código inexistente"""
        cupon, mensaje = Cupon.validar_codigo("NOEXISTE")
        self.assertIsNone(cupon)
        self.assertIn("no encontrado", mensaje.lower())


class CuponAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.cupon = Cupon.objects.create(
            codigo="TEST20",
            tipo="PORCENTAJE",
            valor=Decimal("20.00"),
            estado=True
        )

    def test_validar_cupon_valido(self):
        """Test endpoint de validación de cupón válido"""
        url = '/api/cupones/validar/'
        data = {
            'codigo': 'TEST20',
            'total_reserva': '100.00'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['codigo'], 'TEST20')
        self.assertEqual(response.data['descuento_aplicable'], Decimal('20.00'))

    def test_validar_cupon_inexistente(self):
        """Test endpoint de validación de cupón inexistente"""
        url = '/api/cupones/validar/'
        data = {
            'codigo': 'NOEXISTE',
            'total_reserva': '100.00'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_crear_cupon(self):
        """Test creación de cupón"""
        url = '/api/cupones/'
        data = {
            'codigo': 'NUEVO50',
            'tipo': 'FIJO',
            'valor': '50.00',
            'estado': True
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Cupon.objects.filter(codigo='NUEVO50').exists())

    def test_crear_cupon_porcentaje_invalido(self):
        """Test validación de porcentaje mayor a 100"""
        url = '/api/cupones/'
        data = {
            'codigo': 'INVALIDO',
            'tipo': 'PORCENTAJE',
            'valor': '150.00',
            'estado': True
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
