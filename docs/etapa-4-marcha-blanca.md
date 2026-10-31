# Etapa 4: activación administrativa de marcha blanca

## Objetivo

El registro público permanece deshabilitado. Un administrador puede otorgar **un mes calendario** de marcha blanca a un usuario titular, sin abrir un cobro ni crear una excepción para la aplicación móvil.

Esta activación no es un pago de Mercado Pago. El pago real seguirá el flujo verificado de la etapa de pagos cuando se configure producción.

## Garantías

- No existe un endpoint móvil para otorgar períodos.
- El comando exige un usuario administrador activo (`is_staff=True`) y un motivo obligatorio.
- Solo puede otorgarse al titular, nunca a un usuario secundario.
- El plan se determina en el servidor según los secundarios activos: $50.000, $60.000 o $70.000 CLP.
- Si la cuenta está vencida, el período comienza al otorgarlo. Si aún está vigente, se extiende desde el vencimiento actual.
- Cada decisión queda registrada en `SubscriptionGrant`, visible en modo solo lectura en `/admin/`.

## Uso administrativo

Después de aplicar la migración, un administrador autorizado ejecuta desde el backend:

```powershell
.\.venv\Scripts\python.exe manage.py grant_march_white NOMBRE_TITULAR --actor NOMBRE_ADMINISTRADOR --reason "Marcha blanca aprobada"
```

El comando muestra la fecha de término y el número del registro creado. Se debe conservar el motivo real de la autorización; no usarlo para reemplazar un pago pendiente.

## Antes de usar con una cuenta real

1. Confirmar que la persona es el titular correcto.
2. Confirmar cuántos secundarios activos tiene, porque define el plan mostrado.
3. Ejecutar el comando una sola vez y anotar el resultado en el seguimiento de marcha blanca.
4. Pedir al usuario que actualice BINTRACK; la cuenta saldrá de modo solo lectura mientras el período esté vigente.
