# API Documentation - Sistema de Turismo

## Resumen
API REST para sistema de turismo con gestión de usuarios, servicios, reservas y cupones.

**Base URL:** `http://localhost:8000/api/`

**Documentación Swagger:** `http://localhost:8000/api/docs/`

## Autenticación
La API usa JWT (JSON Web Tokens) para autenticación.

### Obtener Token
```http
POST /api/auth/login/
Content-Type: application/json

{
    "email": "usuario@example.com",
    "password": "password123"
}
```

**Respuesta:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "usuario_id": 1
}
```

### Usar Token
Incluir en headers de requests autenticados:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Endpoints Principales

### 👤 Autenticación y Usuarios

#### Registro de Usuario
```http
POST /api/auth/registro/
Content-Type: application/json

{
    "nombre": "Juan Pérez",
    "email": "juan@example.com",
    "password": "SecretPass123",
    "password_confirm": "SecretPass123",
    "telefono": "71234567"
}
```

#### Mi Perfil
```http
GET /api/usuarios/me/
Authorization: Bearer <token>
```

#### Mis Estadísticas
```http
GET /api/usuarios/mis-estadisticas/
Authorization: Bearer <token>
```

**Respuesta:**
```json
{
    "total_reservas": 5,
    "reservas_pendientes": 1,
    "reservas_pagadas": 3,
    "reservas_canceladas": 1,
    "total_gastado": "450.00",
    "servicios_favoritos": [
        {
            "servicio": "City Tour",
            "count": 2,
            "total_gastado": "200.00"
        }
    ]
}
```

### 🏷️ Catálogo de Servicios

#### Listar Servicios
```http
GET /api/servicios/
```

**Filtros disponibles:**
- `?categoria=1` - Filtrar por categoría
- `?tipo=TOUR` - Filtrar por tipo
- `?search=city` - Buscar en título y descripción

#### Detalle de Servicio
```http
GET /api/servicios/{id}/
```

#### Categorías
```http
GET /api/categorias/
```

### 🎫 Cupones

#### Listar Cupones (Admin)
```http
GET /api/cupones/
Authorization: Bearer <token>
```

#### Validar Cupón
```http
POST /api/cupones/validar/
Authorization: Bearer <token>
Content-Type: application/json

{
    "codigo": "DESC20",
    "total_reserva": "100.00"
}
```

**Respuesta:**
```json
{
    "id": 1,
    "codigo": "DESC20",
    "tipo": "PORCENTAJE",
    "valor": "20.00",
    "estado": true,
    "descuento_aplicable": "20.00",
    "total_con_descuento": "80.00"
}
```

### 📅 Reservas

#### Mis Reservas
```http
GET /api/reservas/mis-reservas/
Authorization: Bearer <token>
```

**Filtros:**
- `?estado=PENDIENTE` - Filtrar por estado

#### Crear Reserva Completa
```http
POST /api/reservas/crear-completa/
Authorization: Bearer <token>
Content-Type: application/json

{
    "servicios": [
        {
            "servicio_id": 1,
            "cantidad": 2,
            "fecha_servicio": "2025-09-15T10:00:00Z"
        }
    ],
    "visitantes": [
        {
            "documento": "12345678",
            "nombre": "Juan",
            "apellido": "Pérez",
            "fecha_nacimiento": "1990-01-01",
            "email": "juan@example.com"
        }
    ],
    "fecha_inicio": "2025-09-15T09:00:00Z",
    "codigo_cupon": "DESC20"
}
```

#### Aplicar Cupón a Reserva
```http
POST /api/reservas/{id}/aplicar-cupon/
Authorization: Bearer <token>
Content-Type: application/json

{
    "codigo_cupon": "DESC20"
}
```

#### Cancelar Reserva
```http
POST /api/reservas/{id}/cancelar/
Authorization: Bearer <token>
Content-Type: application/json

{
    "razon": "Cambio de planes"
}
```

#### Confirmar Pago
```http
POST /api/reservas/{id}/confirmar-pago/
Authorization: Bearer <token>
```

### 🔍 Servicios de Negocio

#### Verificar Disponibilidad
```http
POST /api/disponibilidad/verificar/
Authorization: Bearer <token>
Content-Type: application/json

{
    "servicios_ids": [1, 2, 3],
    "fecha": "2025-09-15T10:00:00Z",
    "cantidad_personas": 4
}
```

**Respuesta:**
```json
{
    "1": {
        "disponible": true,
        "mensaje": "Servicio disponible",
        "capacidad_disponible": 16,
        "servicio_titulo": "City Tour"
    },
    "2": {
        "disponible": false,
        "mensaje": "Capacidad máxima excedida (10)",
        "capacidad_disponible": 2,
        "servicio_titulo": "Hiking Adventure"
    }
}
```

#### Generar Cotización
```http
POST /api/cotizaciones/generar/
Authorization: Bearer <token>
Content-Type: application/json

{
    "servicios": [
        {
            "servicio_id": 1,
            "cantidad": 2
        },
        {
            "servicio_id": 2,
            "cantidad": 1
        }
    ],
    "codigo_cupon": "DESC20"
}
```

**Respuesta:**
```json
{
    "detalles": [
        {
            "servicio_id": 1,
            "servicio_titulo": "City Tour",
            "precio_unitario": "100.00",
            "cantidad": 2,
            "subtotal": "200.00"
        }
    ],
    "subtotal": "200.00",
    "descuento": "40.00",
    "total": "160.00",
    "cupon_valido": true,
    "cupon_mensaje": "Cupón 'DESC20' aplicado",
    "errores": []
}
```

### 👥 Visitantes

#### Buscar Visitante por Documento
```http
GET /api/visitantes/buscar-por-documento/?documento=12345678
Authorization: Bearer <token>
```

## Estados de Reserva

- **PENDIENTE**: Reserva creada, pendiente de pago
- **PAGADA**: Reserva pagada y confirmada
- **CANCELADA**: Reserva cancelada
- **REPROGRAMADA**: Reserva reprogramada

## Tipos de Servicios

- **TOUR**: Tours guiados
- **ALOJAMIENTO**: Hoteles y alojamientos
- **TRANSPORTE**: Servicios de transporte
- **ACTIVIDAD**: Actividades recreativas

## Tipos de Cupones

- **PORCENTAJE**: Descuento por porcentaje (ej: 20%)
- **FIJO**: Descuento de monto fijo (ej: Bs. 50)

## Códigos de Estado HTTP

- `200` - OK
- `201` - Creado exitosamente
- `400` - Error en datos enviados
- `401` - No autenticado
- `403` - Sin permisos
- `404` - Recurso no encontrado
- `500` - Error interno del servidor

## Ejemplos de Casos de Uso

### 1. Flujo Completo de Reserva

1. **Buscar servicios disponibles**
```http
GET /api/servicios/?tipo=TOUR&categoria=1
```

2. **Verificar disponibilidad**
```http
POST /api/disponibilidad/verificar/
{
    "servicios_ids": [1],
    "fecha": "2025-09-15T10:00:00Z",
    "cantidad_personas": 2
}
```

3. **Generar cotización**
```http
POST /api/cotizaciones/generar/
{
    "servicios": [{"servicio_id": 1, "cantidad": 2}],
    "codigo_cupon": "DESC20"
}
```

4. **Crear reserva completa**
```http
POST /api/reservas/crear-completa/
{
    "servicios": [...],
    "visitantes": [...],
    "fecha_inicio": "2025-09-15T09:00:00Z",
    "codigo_cupon": "DESC20"
}
```

5. **Confirmar pago**
```http
POST /api/reservas/{id}/confirmar-pago/
```

### 2. Gestión de Cupones

1. **Crear cupón (Admin)**
```http
POST /api/cupones/
{
    "codigo": "VERANO25",
    "tipo": "PORCENTAJE",
    "valor": "25.00",
    "fecha_inicio": "2025-12-01T00:00:00Z",
    "fecha_fin": "2025-03-01T23:59:59Z",
    "estado": true
}
```

2. **Validar cupón antes de aplicar**
```http
POST /api/cupones/validar/
{
    "codigo": "VERANO25",
    "total_reserva": "200.00"
}
```

## Notas Importantes

1. **Fechas**: Usar formato ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)
2. **Decimales**: Usar strings para valores monetarios precisos
3. **Autenticación**: Todos los endpoints excepto registro y login requieren autenticación
4. **Roles**: Algunos endpoints están restringidos a usuarios ADMIN
5. **Validaciones**: La API incluye validaciones de negocio (fechas, capacidades, etc.)

## Testing

Para testing manual, se pueden usar herramientas como:
- **Postman**: Importar endpoints desde la documentación Swagger
- **curl**: Ejemplos en línea de comandos
- **Swagger UI**: Interfaz web en `/api/docs/`