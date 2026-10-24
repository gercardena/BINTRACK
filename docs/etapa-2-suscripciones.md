# Etapa 2: calendario mensual y acceso (solo local)

## Reglas implementadas

- El servidor consulta la suscripción del principal, también para los secundarios. Una suscripción histórica propia del secundario o el indicador antiguo `suscripcion_activa` no conceden permisos adicionales.
- Antes del vencimiento: operaciones completas. Desde el instante del vencimiento y durante **72 horas**: período de gracia con las mismas operaciones. En el instante exacto en que terminan las 72 horas: solo lectura.
- Una cuenta sin suscripción, inactiva o cuyo período todavía no empieza tiene acceso de solo lectura, sin gracia adicional.
- Las cuentas de usuario desactivadas siguen sin acceso; solo lectura no las reactiva.
- Se mantienen los datos, la separación entre negocios, los reportes y la consulta de comprobantes. No se eliminan ventas, productos, pagos ni movimientos al vencer.
- Se bloquean POST/PUT/PATCH/DELETE de las 18 vistas de negocio: clientes, envases, movimientos, productos, presentaciones, stock, ventas y artículos, confirmación/pago/cancelación de venta, pagos y generación/edición de comprobantes. La exportación de datos ya consultados a PDF no registra una operación nueva.
- El principal conserva la administración de usuarios/suscripción (incluida la desactivación de secundarios). Esta excepción administrativa no permite modificar operaciones del negocio ni las fechas desde la app.

## Calendario y renovaciones

`renew_monthly_period` es una función interna preparada para la siguiente etapa, **no un endpoint para activar suscripciones ni una prueba de pago**. No está conectada a los callbacks históricos de Mercado Pago.

- Primer período: un mes de calendario desde la activación validada.
- Renovación: suma un mes al vencimiento registrado, incluso después de la gracia, según la decisión del usuario. No se reinicia desde la fecha de pago.
- Se conserva el día de facturación en meses cortos: 31 de enero → 28/29 de febrero → 31 de marzo. Horarios calculados en America/Santiago, normalizando horas inexistentes por cambio de horario.
- Si hay varios meses de atraso, sumar uno puede dejar la cuenta todavía vencida. Esta función no perdona meses, no cobra deudas y no determina cuántos períodos se pagan. Esa conciliación corresponde a la etapa de pagos.
- Las altas de secundarios no cambian la fecha del principal. El cargo adicional completo y el control de períodos ya pagados siguen pendientes de la integración de pagos.

La migración `0005_usersubscription_dia_facturacion` agrega un campo opcional. **No renueva ni cambia las fechas, planes o estados existentes**. Para suscripciones históricas sin ancla, la primera renovación toma el día del vencimiento registrado.

## API e interfaz

El perfil, el estado de suscripción y el resumen del principal incorporan `suscripcion_acceso`: `estado`, `puede_operar`, `solo_lectura`, `fecha_fin`, `gracia_hasta` y `dias_gracia`.

Una escritura bloqueada devuelve HTTP 403 con `code: subscription_read_only`. La app muestra un mensaje específico y no cierra la sesión por ese motivo. No reintenta la operación como si fuera un error de autenticación.

Inicio y Usuarios y suscripción muestran el estado y las fechas. Inicio refresca el perfil al abrirse, al volver de módulos, al regresar a primer plano, mediante el botón actualizar y cada minuto mientras es visible. El servidor sigue siendo la autoridad en cada petición aunque el aviso de la pantalla esté momentáneamente desactualizado. El acceso directo Nueva venta se deshabilita; los formularios ya abiertos reciben el bloqueo al intentar guardar y conservan sus datos según su manejo de errores existente.

## Pruebas locales

Las pruebas usan una base PostgreSQL independiente y eliminable, no las cuentas reales de prueba. Cubren límites temporales exactos, cambio de horario chileno, febrero/años bisiestos, meses atrasados, permisos de principal/secundarios, rutas de escritura y consulta, aislamiento entre negocios, conservación de datos y cobertura de las vistas registradas.

Para comprobar en el teléfono: reiniciar el backend local después de migrar y reiniciar Flutter apuntando a ese backend. Revisar el aviso en Inicio y en Usuarios y suscripción. Una cuenta local ya vencida aparecerá en solo lectura; **no cambiar sus fechas ni simular pagos sin autorización**. El estado activo/gracia/vencido se verifica con el reloj controlado de las pruebas automáticas, sin tocar períodos reales.

## Verificación manual local confirmada

El usuario comprobó en el teléfono, con las cuentas principal y secundaria en solo lectura:

- Ambos pueden consultar los módulos y no pueden abrir Nueva venta.
- Solo el principal puede abrir Usuarios y suscripción; el acceso no aparece para el secundario.
- No se cambiaron fechas de las cuentas para estas pruebas. La revisión manual de período activo y gracia quedó pospuesta; esos estados están cubiertos por las pruebas automatizadas.

Esta comprobación de navegación no sustituye las pruebas del servidor que bloquean las escrituras en todos los módulos.

## Pendiente antes de publicar

- Integración Mercado Pago con importes correctos y confirmación verificada e idempotente. Los endpoints históricos de pagos conservan reglas antiguas: no usarlos para probar o cobrar los nuevos planes.
- Avisos de vencimiento por correo y demás notificaciones de la etapa 4.
- Completar las pruebas manuales de período activo y gracia antes de publicar. No se generó un nuevo APK ni se desplegó en Render como parte de esta etapa.
