# Etapa 1: planes y usuarios (solo local)

## Alcance

- Catálogo mensual: principal $50.000 CLP; un secundario $60.000; dos $70.000. Precios finales.
- Un principal y como máximo dos secundarios **activos**. Se conservan las cuentas inactivas y sus relaciones históricas.
- Solo el principal administra la cuenta. Un secundario con el rol antiguo `admin` tampoco puede hacerlo.
- Los secundarios mantienen los permisos operativos que ya tenían sobre el negocio del titular.
- Alta, edición de datos de contacto y desactivación/reactivación. No se expone eliminación, cambio de titular, cambio de identidad ni asignación de privilegios.
- Una nueva cuenta siempre se crea: no se permite vincular un usuario preexistente de otro negocio.
- Las contraseñas se validan y guardan como hashes; nunca se devuelven en la respuesta.
- El bloqueo por desactivación se comprueba también con un JWT emitido previamente. Una relación inactiva no convierte al secundario en titular.
- Las altas/reactivaciones bloquean la fila del titular durante la transacción para evitar superar el límite mediante peticiones simultáneas.

## Compatibilidad y migración

`accounts.0004_planes_mensuales` agrega dos campos y tres planes identificados por código. No modifica precios de planes históricos, usuarios, vencimientos ni asociaciones de suscripciones existentes. Si una cuenta histórica excede dos secundarios activos, se informa para revisión sin borrar usuarios.

La pantalla presenta una **referencia mensual según los usuarios activos**, no un pago confirmado ni un saldo exigible. Crear/desactivar usuarios no cambia la suscripción, las fechas o el dinero cobrado. Los tres nuevos planes no se asignan automáticamente a períodos anteriores.

## API

- `GET /api/accounts/cuenta/`: catálogo, referencia mensual, vigencia existente y secundarios del principal.
- `POST /api/accounts/cuenta/`: crea un secundario. Campos: `username`, `email`, `password`, opcionales `first_name`, `last_name`, `telefono`.
- `PUT /api/accounts/cuenta/usuarios/{id}/`: datos de contacto y/o `activo`. El id corresponde a la relación. Campos protegidos o desconocidos se rechazan.
- El perfil incorpora `puede_gestionar_cuenta`; Flutter usa esta capacidad para mostrar el acceso. El servidor aplica la autorización independientemente de la interfaz.

## Prueba manual local

1. Reiniciar Django local y ejecutar Flutter apuntando a ese servidor, no a Render.
2. Entrar con el principal y abrir **Usuarios y suscripción**. Confirmar el vencimiento sin cambios.
3. Crear secundarios con credenciales de prueba; comprobar las referencias $60.000/$70.000. El tercero activo debe rechazarse.
4. Entrar con un secundario: conserva las operaciones del negocio, sin acceso a la administración.
5. Desactivarlo desde el principal: una sesión existente debe perder acceso al servidor; sus operaciones no se eliminan.
6. Reactivarlo si hay cupo. Comprobar que no cambia su identidad ni la fecha del titular.

## Fuera de alcance / antes de publicar

- No se llama a Mercado Pago desde esta pantalla. Los endpoints históricos de pagos y su tarifa antigua **no constituyen la nueva integración y no deben usarse para cobrar estos planes**; se reemplazarán y probarán en la etapa 3.
- La respuesta `cobro_habilitado: false` describe esta pantalla/etapa, no desactiva los endpoints históricos.
- La activación condicionada al pago, cargo completo por alta adicional, cambios de cupos facturados, renovación mensual de calendario y tres días de gracia se completarán en etapas 2 y 3. Por ahora el alta habilita al usuario para pruebas locales sin cobrar.
- No se supone devolución ni descuento de un período ya pagado al desactivar un secundario. Las reglas de baja/reactivación facturada deben terminarse antes de cobrar.
- Avisos/correos e historial integral de operaciones corresponden a la etapa 4. Se conserva el historial de comprobantes ya implementado.
- No desplegar esta etapa aislada como sistema comercial de suscripciones completo.

## Verificación

`apps.accounts.tests_management` cubre catálogo, permisos, aislamiento entre titulares, contraseñas, cupos, preservación de suscripciones y revocación por desactivación.
La prueba de altas concurrentes requiere PostgreSQL y se omite en SQLite. Ejecutar siempre con una base de pruebas separada; no usar datos reales como base de pruebas.
