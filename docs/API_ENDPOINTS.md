# API Endpoints BINTRACK

Base URL local:

```text
http://127.0.0.1:8000/api
En dispositivo físico usar la IP local del PC:
http://<IP_PC>:8000/api
Todos los endpoints protegidos requieren:
Authorization: Bearer <access_token>
Content-Type: application/json
Auth
Login
POST /api/auth/login/
Body:
{
  "email": "usuario@example.com",
  "password": "password"
}
Refresh token
POST /api/auth/refresh/
Body:
{
  "refresh": "<refresh_token>"
}
Usuario / cuenta
Perfil usuario
GET /api/accounts/user/profile/
Clientes
Listar clientes
GET /api/clientes/
Crear cliente
POST /api/clientes/
Body:
{
  "nombre": "Cliente Demo",
  "rut": "11111111-1",
  "email": "demo@test.cl",
  "telefono": "56911111111",
  "direccion": "Santiago",
  "activo": true
}
Notas:
El RUT se valida y normaliza.
El RUT es único por usuario.
usuario es asignado automáticamente por backend.
Ver cliente
GET /api/clientes/<id>/
Actualizar cliente
PUT /api/clientes/<id>/
Desactivar cliente
DELETE /api/clientes/<id>/
Nota:
No borra físicamente.
Cambia activo a false.
Tipos de envase
Listar tipos de envase
GET /api/bins/types/
Crear tipo de envase
POST /api/bins/types/
Body:
{
  "nombre": "Bin Azul",
  "tipo": "BIN",
  "material": "Plástico",
  "valor_deposito": "60000.00"
}
Ver tipo de envase
GET /api/bins/types/<id>/
Actualizar tipo de envase
PUT /api/bins/types/<id>/
Eliminar tipo de envase
DELETE /api/bins/types/<id>/
Movimientos de envases
Listar movimientos
GET /api/bins/movements/
Crear movimiento
POST /api/bins/movements/
Body entrada:
{
  "cliente": 1,
  "bin_type": 3,
  "tipo_movimiento": "entrada",
  "cantidad": 100,
  "deposito_pagado": "0.00",
  "referencia": "Stock inicial Bin Azul"
}
Body préstamo:
{
  "cliente": 1,
  "bin_type": 3,
  "tipo_movimiento": "prestamo",
  "cantidad": 1,
  "deposito_pagado": "0.00",
  "referencia": "Préstamo manual"
}
Tipos de movimiento:
entrada
prestamo
devolucion
baja
Balance por cliente/envase
GET /api/bins/balance/
Clientes para movimientos
GET /api/bins/clientes/
Inventario
Resumen inventario
GET /api/inventario/
Respuesta ejemplo:
[
  {
    "bin_type_id": 3,
    "bin_nombre": "Bin Azul",
    "entradas": 100,
    "prestamos": 1,
    "devoluciones": 0,
    "bajas": 0,
    "en_clientes": 1,
    "llenos": 49,
    "disponible": 50
  }
]
Cálculo principal:
disponible = entradas - en_clientes - llenos - bajas
Listar stock de producto/envase
GET /api/inventario/stock/
Crear stock
POST /api/inventario/stock/
Body:
{
  "product": 5,
  "bin": 3,
  "cantidad": 50
}
Actualizar stock
PUT /api/inventario/stock/<id>/
Productos
Listar productos
GET /api/productos/
Crear producto
POST /api/productos/
Body:
{
  "nombre": "Ciruelas",
  "descripcion": "Ciruelas negras",
  "precio": "250000.00",
  "activo": true
}
Nota:
El precio del producto se conserva como base temporal.
El precio real de venta debe venir desde la presentación.
Ver producto
GET /api/productos/<id>/
Actualizar producto
PUT /api/productos/<id>/
Eliminar producto
DELETE /api/productos/<id>/
Presentaciones de producto
Listar presentaciones
GET /api/productos/presentations/
Crear presentación
POST /api/productos/presentations/
Body:
{
  "product": 5,
  "bin_type": 3,
  "precio": "250000.00",
  "activo": true
}
Ver presentación
GET /api/productos/presentations/<id>/
Actualizar presentación
PUT /api/productos/presentations/<id>/
Eliminar presentación
DELETE /api/productos/presentations/<id>/
Notas:
Una presentación activa conecta producto + tipo de envase + precio.
No se debe desactivar una presentación con stock lleno.
Ventas
Listar ventas
GET /api/ventas/sales/
Crear venta
POST /api/ventas/sales/
Body:
{
  "cliente": 1
}
Notas:
La venta inicia en estado draft.
No se permite cliente inactivo.
Ver venta
GET /api/ventas/sales/<id>/
Eliminar venta borrador
DELETE /api/ventas/sales/<id>/
Confirmar venta
POST /api/ventas/sales/<id>/confirm/
Notas:
Descuenta stock lleno.
Registra préstamo de envases.
La venta pasa a confirmed.
Cancelar venta
POST /api/ventas/sales/<id>/cancel/
Notas:
Aplica a ventas confirmadas.
Devuelve stock lleno.
Registra devolución de envases.
La venta pasa a cancelled.
Items de venta
Crear item de venta
POST /api/ventas/items/
Body:
{
  "sale": 1,
  "product": 5,
  "bin": 3,
  "cantidad": 1
}
Notas:
Backend determina precio_unitario.
Backend determina bins_cantidad.
Solo se pueden modificar ventas en estado draft.
Eliminar item de venta
DELETE /api/ventas/items/<id>/
Pagos
Listar pagos
GET /api/pagos/
Registrar pago
POST /api/pagos/
Body:
{
  "sale": 1,
  "metodo": "transferencia",
  "referencia": "PAGO-DEMO"
}
Notas:
No hay abonos parciales.
El pago toma el total de la venta.
La venta pasa de confirmed a paid.
No se permite pago duplicado.
Facturas
Listar facturas
GET /api/facturas/
Generar factura
POST /api/facturas/<sale_id>/generar/
Notas:
La factura es opcional.
Puede generarse para venta paid.
Si ya existe, devuelve la factura existente.
Guarda snapshot del cliente y totales.
Flujo recomendado
Crear cliente.
Registrar entrada de envases.
Crear producto.
Crear presentación.
Crear stock inicial.
Crear venta.
Agregar item.
Confirmar venta.
Registrar pago.
Emitir factura.
Revisar inventario.