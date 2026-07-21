Ese documento debería dejar claro:
cómo funcionará la suscripción mensual;
qué rol tiene suscripcion_activa;
qué opciones de pago evaluamos;
qué haremos ahora;
qué dejamos para después.


# Modelo de suscripciones y pagos mensuales

## Objetivo

Definir cómo BinTrack controlará el acceso de usuarios mediante una suscripción mensual, sin amarrar la app desde el inicio a un único proveedor de pago.

## Principio principal

El backend será quien decida si un usuario tiene acceso activo a BinTrack.

La app móvil no debe confiar directamente en Mercado Pago, Webpay o Google Play para decidir el acceso. La app consulta el perfil del usuario y usa el campo `suscripcion_activa`.

## Estado actual

Actualmente el backend ya tiene el campo:

- `suscripcion_activa`

Este campo indica si el usuario puede usar la aplicación.

## Flujo recomendado

1. El usuario inicia sesión.
2. La app consulta el perfil del usuario.
3. El backend responde si la suscripción está activa.
4. Si `suscripcion_activa` es `true`, el usuario entra normalmente.
5. Si `suscripcion_activa` es `false`, la app muestra una pantalla amable indicando que debe activar o renovar su plan.

## Proveedores posibles

### Activación manual

Útil para el primer MVP.

Permite activar usuarios desde administración mientras se valida el modelo comercial.

### Mercado Pago

Buena opción para pagos directos, clientes empresa o suscripciones fuera de Google Play.

### Webpay

Buena opción para pagos en Chile, especialmente si el pago se realiza desde una web o flujo externo.

### Google Play Billing

Opción recomendada si la app se publica en Google Play y la suscripción se compra dentro de la app Android.

## Estrategia recomendada

Primero implementar control interno de suscripción en backend.

Luego integrar proveedores de pago sin cambiar la lógica principal de acceso.

## MVP recomendado

Para una primera versión:

- mantener `suscripcion_activa`;
- mostrar una pantalla clara si la suscripción no está activa;
- permitir activación manual desde backend/admin;
- dejar preparado el modelo para agregar Mercado Pago, Webpay o Google Play Billing después.

## No implementar todavía

Por ahora no conviene partir integrando pagos complejos hasta confirmar:

- canal de venta principal;
- si la app irá a Google Play;
- si los clientes pagarán desde la app, desde una web o manualmente;
- política comercial mensual.



## Pendiente: bloqueo suave en la app

Por ahora BinTrack muestra el estado de suscripción en el Home, pero no bloquea módulos operativos.

La decisión recomendada para una versión futura es aplicar un bloqueo suave:

Usuarios sin suscripción activa pueden:
- iniciar sesión;
- ver el Home;
- ver el estado de suscripción;
- abrir la Guía de usuario;
- cerrar sesión.

Usuarios sin suscripción activa no deberían usar módulos operativos:
- Nueva venta;
- Clientes;
- Envases;
- Productos;
- Inventario;
- Ventas;
- Pagos;
- Comprobantes.

Mensaje recomendado:

"Suscripción requerida. Activa tu plan mensual para usar este módulo."

Motivo de dejarlo pendiente:
- evitar bloquear pruebas internas;
- permitir demos;
- confirmar primero el flujo comercial;
- definir antes si el pago será manual, Mercado Pago, Webpay o Google Play Billing.