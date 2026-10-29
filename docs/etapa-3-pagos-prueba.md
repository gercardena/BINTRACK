# Etapa 3A: backend de cobros, exclusivamente de prueba

## Estado y límites

Implementación local. No se habilitan pagos reales, no se llama al proveedor durante
las pruebas automatizadas, no se cambian las credenciales históricas y no se publica
en Git/Render. Flutter permanece igual: todavía no ofrece un botón de pago.

Se prepara el pago de **un período mensual** según los secundarios activos: CLP
50.000 / 60.000 / 70.000, precios finales. No es débito automático.

Esta etapa **NO completa** la facturación por alta de un secundario a mitad del mes,
la activación condicionada al pago de ese adicional, conciliación de varios meses
atrasados, devoluciones automáticas ni notificaciones por correo. Por ese motivo no
debe habilitarse como sistema comercial completo. La gestión de secundarios conserva
el comportamiento local de las etapas anteriores y `cobro_habilitado` sigue en false.

## Controles implementados

- Solo el principal crea y consulta sus órdenes. Importe, moneda, plan, secundarios
  y vencimiento se calculan en el servidor; no se aceptan importes desde el cliente.
- Cada orden nueva tiene una referencia UUID, fotografía de su plan/usuarios/período
  y validez del enlace de 24 horas. La referencia se guarda antes de llamar a MP.
- Repetir la creación reutiliza el enlace pendiente; si hay una llamada incierta o
  cambió la cuenta, se solicita revisión en vez de generar cobros repetidos.
- Las nuevas credenciales de prueba están separadas de las antiguas. Antes de crear
  una preferencia se consulta `/users/me`: deben coincidir el vendedor configurado,
  el país CL y la etiqueta `test_user`. Si falta esa evidencia no se genera el enlace.
- El retorno del navegador nunca activa una suscripción. El proveedor se consulta
  desde el backend y se compara id, referencia, monto total exacto, moneda CLP,
  vendedor, `live_mode=false`, estado y fechas. No se usa el neto tras comisiones.
- El webhook valida HMAC-SHA256 de `x-signature`, `x-request-id`, `data.id` y `ts`,
  con comparación constante. Exige `type=payment` y coincidencia del cuerpo con el
  identificador firmado. El receptor IPN antiguo y `merchant_order` no activan pagos.
- Se conservan intentos con id del proveedor único. La renovación y el registro de
  su aplicación son una sola transacción con bloqueo por principal y orden.
  Notificaciones repetidas o simultáneas no suman otro mes.
- La renovación usa el calendario mensual y conserva el vencimiento anterior,
  incluso en gracia o vencido, sin duplicar la fila de suscripción. Una renovación
  puede dejar vencida una cuenta con varios meses de atraso: no se condona deuda.
- Si cambian usuarios, plan o vencimiento entre la orden y el pago, se registra para
  revisión y no se conceden períodos/cupos silenciosamente.
- Reembolsos, contracargos, disputas, pagos parciales reembolsados y segundos pagos
  aprobados de una orden requieren revisión. No se borran ventas ni se acortan
  fechas automáticamente. No hay todavía interfaz para resolver esas incidencias.
- Ante errores se devuelve un mensaje seguro, nunca credenciales ni la respuesta
  completa del proveedor. Los errores transitorios de consulta responden 503 para
  permitir reintentos. Un fallo de creación queda pendiente de revisión.

## Configuración posterior (no habilitada en esta implementación)

En el `.env` local, nunca en Git ni en una conversación, harán falta estas variables:

```dotenv
MERCADOPAGO_ENV=sandbox
MERCADOPAGO_TEST_ENABLED=false
MERCADOPAGO_TEST_ACCESS_TOKEN=
MERCADOPAGO_TEST_COLLECTOR_ID=
MERCADOPAGO_TEST_WEBHOOK_SECRET=
MERCADOPAGO_TEST_NOTIFICATION_URL=
MERCADOPAGO_TEST_SUCCESS_URL=
MERCADOPAGO_TEST_FAILURE_URL=
MERCADOPAGO_TEST_PENDING_URL=
```

No copiar las claves antiguas sin verificar el entorno en Mercado Pago Developers.
El prefijo del token y `DEBUG` no demuestran que una credencial sea de prueba.
Las URLs deben ser HTTPS. Para notificaciones a un backend local hará falta un túnel
HTTPS público aprobado por el usuario, con URL vigente. No se inicia uno aquí.

`MERCADOPAGO_ENV=production` queda bloqueado aunque TEST_ENABLED sea true. Una futura
integración productiva requiere una etapa explícita y no un cambio casual de DEBUG.

## API

- `POST /api/payments/crear/`, JSON `{}`: crea/reutiliza una orden de prueba. 201 nueva,
  200 reutilizada, 409 si requiere revisión, 503 si no está habilitada/configurada.
- `GET /api/payments/confirmar/?payment_id=<id LOCAL>`: consulta solo lectura del
  principal. No contacta a MP ni activa suscripciones. Oculta enlaces ya aplicados,
  vencidos o en revisión. No es la URL pública de retorno del checkout.
- `POST /api/payments/verificar/<id LOCAL>/`, JSON `{"provider_payment_id":"..."}`:
  consulta autenticada del principal que concilia el pago mediante las mismas
  validaciones del webhook y exige que corresponda a su propia orden. Útil para
  comprobaciones de sandbox cuando no llegan notificaciones; no simula aprobación.
- `POST /api/payments/webhook/?data.id=<id MP>&type=payment`: notificación firmada.
- `POST /api/payments/simular-aprobado/<id>/`: retirado (410); no activa nada.

Los pagos históricos conservan sus datos, pero no reciben referencias nuevas ni
se aplican retroactivamente. `activate_subscription_for_user` es una función antigua
sin llamadas desde las rutas de pago; la ruta nueva usa `renew_monthly_period`.

## Verificación y siguientes pasos

`apps.payments.tests` usa proveedor simulado y prohíbe red. Incluye límites de precio,
aislamiento de cuentas, firmas, datos incorrectos, repetición, concurrencia real en
PostgreSQL, renovación de cuentas activas/en gracia/vencidas y rollback transaccional.
Las pruebas se ejecutan en una base PostgreSQL temporal independiente.

Verificación local completada: 70 pruebas aprobadas (34 de pagos y 36 de
regresión de cuentas, acceso por suscripción y comprobantes), sin llamadas reales
al proveedor. La base temporal de pruebas fue eliminada al finalizar.

El 25/10/2026 se aplicó `payments.0002_verified_test_checkout` exclusivamente a la
base PostgreSQL local, con cobros deshabilitados. Se compararon los datos antes y
después dentro de una transacción: las 2 suscripciones conservaron todos sus datos
y vencimientos. No había pagos históricos en esa base (0 filas). La revisión de
Django y la comprobación de migraciones pendientes de generar no detectaron problemas.

Antes de probar con Mercado Pago: revisar la cuenta/app de prueba, configurar las
URLs de retorno y notificaciones, confirmar credenciales sin exponerlas y acordar
la cuenta local que recibirá la renovación de prueba. No modificar el vencimiento
de las cuentas actuales sin autorización. La prueba manual con el proveedor y el
botón de Flutter siguen pendientes; pasar tests simulados no demuestra integración
real con Mercado Pago.

Referencias oficiales consultadas:
- [Notificaciones de Checkout Pro](https://www.mercadopago.cl/developers/en/docs/checkout-pro-preferences/payment-notifications)
- [Cuentas de prueba](https://www.mercadopago.cl/developers/es/docs/checkout-pro-preferences/test-accounts)
- [Creación de preferencias](https://www.mercadopago.cl/developers/es/reference/online-payments/checkout-pro-preferences/create-preference/post)

## Receptor temporal local (autorizado el 25/10/2026)

`scripts/mp_test_gateway.py --tunnel --minutes 90` inicia un receptor solamente
en 127.0.0.1:8765 y un proceso ngrok propio, sin inspección local de solicitudes.
Se cierra automáticamente junto con ngrok al vencer el plazo (máximo 90 minutos).
No se apunta el túnel directamente al puerto 8000 de Django. El túnel es público
y utiliza la infraestructura de ngrok; no equivale a un despliegue productivo.

- Solo POST a `/api/payments/webhook/` se reenvía a Django en 127.0.0.1:8000.
  Requiere JSON limitado a 64 KiB y encabezados de firma; la autenticidad de la
  firma se comprueba en Django. Solo esos encabezados se reenvían, no cookies ni
  Authorization. Se ocultan respuestas internas, errores de depuración y redirects.
- `/mp-test/health` y `/mp-test/success`, `/mp-test/failure`, `/mp-test/pending`
  son respuestas estáticas sin acceso a datos. Nunca activan una suscripción.
- El resto de las rutas queda bloqueado. Concurrencia limitada a 8 conexiones,
  tiempos de espera de 10 segundos. No se guardan cuerpos ni credenciales en logs.
- 7 pruebas del receptor pasan con `python -m unittest scripts.test_mp_test_gateway`.
- Si Django está apagado o los cobros están deshabilitados, una notificación no se
  confirma: responde 503. No habilitar TEST_ENABLED solo para obtener un HTTP 200.

El token de vendedor fue validado mediante GET de solo lectura a `/users/me`:
coinciden el vendedor esperado, el país CL y la etiqueta test_user. No se creó
ningún pago. La clave de Webhooks y las pruebas completas siguen pendientes.
La dirección pública es temporal; verificar su vigencia antes de configurarla.
Para cierre anticipado, terminar únicamente los procesos ngrok y gateway de esta
sesión (sus identificadores se anotan al iniciarla), nunca otros servidores.

## Punto de continuación al terminar el 25/10/2026

El usuario pidió continuar mañana. No crear nuevas cuentas, activar cobros ni
iniciar pagos hasta que retome. Token y clave Webhooks guardados solo en `.env`,
excluido de Git. Las cuatro URLs TEST fueron completadas, pero son temporales:
no asumir que seguirán vigentes al reabrir el túnel.

El vendedor de prueba tiene la aplicación TestApp-b4a0ee81 (Checkout Pro). El
usuario guardó la URL en Modo de prueba con solo Pagos (legacy) seleccionado.
El backend mantiene `MERCADOPAGO_TEST_ENABLED=false`; no hay órdenes locales
de pago (0) y siguen las 2 suscripciones existentes, sin renovación por esta prueba.

Próximo paso pendiente de respuesta: elegir/autorizar un principal de BINTRACK
exclusivo para la prueba, para no modificar la cuenta habitual ni piloto001.
Después: reabrir y verificar túnel restringido, actualizar URLs locales y del
panel si cambiaron, iniciar el backend local y acordar la habilitación de pruebas.
Faltan la notificación auténtica de Mercado Pago y el pago completo con comprador
de prueba. No afirmar que la integración completa funciona por haber pasado mocks.
No se ha publicado esta etapa en Git/Render ni generado un APK.

### Continuación 26/10/2026

Con autorización del usuario se creó `mp_prueba_local` (id local 3), principal
activo sin privilegios staff/superuser ni secundarios. No tiene suscripción ni
pagos y su referencia mensual es CLP 50.000. Se creó con contraseña inutilizable;
asignar una contraseña local mediante `manage.py changepassword mp_prueba_local`
antes de probar login. No almacenar esa contraseña en esta documentación.

Se verificó dentro de la transacción que todos los usuarios anteriores, las
suscripciones, las asociaciones y los pagos conservaron exactamente sus datos.
TEST_ENABLED sigue false. No se reabrió el túnel ni se creó un enlace de pago.
Esta cuenta sustituye la elección pendiente del apartado anterior. Primero se
probará el alta inicial (sin vencimiento previo), después la renovación y la
repetición de notificaciones, siempre sin afectar las cuentas habituales.

La contraseña de `mp_prueba_local` ya fue asignada por el usuario y se verificó
`has_usable_password`, sin leerla ni probar un login con ella. El 26/10 a las 19:34
(Chile) se reabrió el gateway (PID 2940, ngrok PID 16404), con cierre automático
90 minutos después. Las comprobaciones públicas de salud, rutas bloqueadas y
rechazo de webhook sin firma pasaron. Las URLs TEST del `.env` fueron actualizadas
al nuevo túnel. Pendiente: el usuario debe actualizar la URL en el panel Webhooks
de la aplicación del vendedor. TEST_ENABLED sigue false, Django no está iniciado
y todavía no se creó ninguna orden de pago para esta cuenta.

### Primer enlace de prueba generado (26/10, 19:46 Chile)

Tras autorización explícita se creó una única orden local (Payment id 1) para
`mp_prueba_local`, CLP 50.000, estado pending. Mercado Pago devolvió la preferencia
del vendedor de prueba esperado. La URL está en Payment.checkout_url; reutilizar
esa orden, no crear una nueva si el usuario aún no completó el pago.
Todas las suscripciones conservaron sus datos tras crear el enlace.

El `.env` sigue con TEST_ENABLED=false. La creación usó un override limitado a
esa llamada. `scripts/mp_test_receiver.py --minutes 60` habilita exclusivamente
sandbox dentro de un proceso temporal (PID 13032), iniciado 19:45:40, con cierre
aproximado 20:45:40. Solo sirve POST al webhook, incluso desde localhost:8000;
otras rutas responden 404. DEBUG=false en ese proceso. Se verificó mediante el
túnel que una firma falsa se rechaza con 401. No es un servidor general para Flutter.

El usuario debe abrir el enlace y entrar como Buyer Test User, nunca con su cuenta
personal ni el vendedor. Pendiente pago de prueba, notificación auténtica y consulta
verificada del resultado. Generar preferencia no equivale a pago aprobado.
La preferencia vence el 27/10 19:46 Chile, pero el receptor y túnel cierran antes:
comprobar ambos antes de pedir al usuario que confirme un pago.

### Diagnóstico local 27/10/2026

El usuario completó el pago de prueba 186266211828 el 26/10. La consulta
autenticada al proveedor confirmó approved/accredited, CLP 50.000, referencia
coincidente con Payment 1, collector 3081058524 y payer 3081058526. El vendedor
fue verificado con /users/me como test_user de Chile. La consulta pública del
comprador no incluye tags: no interpretar esa ausencia como cuenta real.
La respuesta del pago contiene live_mode=true; reconcile exige false y no debe
eliminarse esa protección sin resolver la identificación segura del entorno.

El panel del proveedor mostró payment.created en ambiente Productivo con entrega
502. No hay cuerpo de respuesta ni registros históricos suficientes para atribuir
la causa. El gateway convierte fallas de conexión al backend en 503, no 502.
El cierre del receptor a las 20:45 es posterior al envío de las 20:30 y no prueba
la causa de esa entrega fallida. Payment 1 sigue pendiente, sin aplicación ni
PaymentAttempt. No repetir el pago ni crear otra preferencia.

Se añadieron diagnósticos de fecha UTC, componente, evento fijo y código HTTP en
los scripts locales. No registran URLs, cuerpos, cabeceras, claves, direcciones
de clientes ni textos de excepciones. Nueve pruebas aisladas del gateway y del
formato de registros pasan; manage.py check no detecta problemas. No se modificó
la conciliación, la base de datos ni .env. TEST_ENABLED permanece false y no se
reabrieron los servicios públicos. Para diagnosticar una entrega auténtica será
necesario reabrir temporalmente el receptor restringido y solicitar el reenvío
de la misma notificación, no un nuevo pago. Sigue pendiente resolver live_mode.

### Excepción acotada para cuentas de prueba (27/10)

Se incorporó una alternativa opt-in para la respuesta live_mode=true observada
en Checkout Pro con usuarios de prueba. No se cambia ni se confía en el indicador
de la notificación: el dato procede de la consulta autenticada del pago.
Además de sandbox y TEST_ENABLED, requiere simultáneamente:

- MERCADOPAGO_TEST_ALLOW_TEST_USERS_LIVE_MODE=true (false por defecto).
- MERCADOPAGO_TEST_BUYER_ID igual al payer.id del pago, distinto del vendedor.
- MERCADOPAGO_TEST_LOCAL_OWNER_ID igual al principal de la orden local.
- Verificación fresca de /users/me con el token configurado: vendedor esperado,
  país CL y etiqueta test_user. Error de red o identidad no verificada bloquea.
- Las validaciones existentes de referencia, moneda, importe, fechas, estado y
  snapshot de cuenta permanecen; también los bloqueos e idempotencia.

El comprador autorizado debe provenir del panel de cuentas de prueba del usuario;
la consulta pública /users/{id} no acredita esa condición. No habilitar esta
excepción para una cuenta habitual ni usarla como configuración de producción.
No se modificó .env ni se aplicó Payment 1 al implementar este cambio.
37 pruebas de pagos pasaron en una base PostgreSQL temporal independiente,
incluyendo webhook repetido para live_mode=true, rechazo de vendedor real,
vendedor/país incorrectos, fallo del proveedor, comprador/principal incorrectos,
ausencia de opt-in y la prueba existente de conciliación concurrente.
Pendiente habilitación limitada para el principal de prueba y verificación
end-to-end. Los procesos ya iniciados deben reiniciarse para cargar el cambio.

El usuario autorizó habilitación limitada y reinicio el 27/10. A las 19:12 Chile
se inició receptor PID 18752 con --minutes 50 --test-buyer-id 3081058526. El
principal se resuelve exclusivamente por username mp_prueba_local (id 3). La
excepción solo vive en ese proceso: .env permanece deshabilitado. Log temporal
bintrack-mp-receiver-20261027-191159.out.log. Se conserva el túnel de las 18:35,
con cierre previsto alrededor de las 20:05; el receptor vence aproximadamente
20:02. Pendiente reenvío por el usuario del recurso 186266211828 y comprobación
de activación única. No crear otro pago. Antes del reenvío solo existen las dos
suscripciones previas, y Payment 1 sigue pending, sin aplicar.

### Resultado de la prueba manual 27/10, 19:16–19:18 Chile

El simulador del panel envió payment.updated para el pago existente 186266211828.
El receptor respondió 200 a las 22:16:38 UTC, consultó el pago al proveedor y
aplicó Payment 1 a mp_prueba_local. Inicio 2026-10-26T23:30:08Z (aprobación del
pago), vencimiento 2026-11-26T23:30:08Z, día de facturación 26. Sin needs_review.
La repetición por el usuario respondió 200 a las 22:17:58 UTC y conservó
exactamente applied_at, applied_until y fecha_fin: una sola PaymentAttempt y
una sola suscripción para ese principal. Ambas suscripciones anteriores
conservaron todos sus valores.

Se validó recepción mediante simulador firmado y consulta del pago aprobado;
esto no prueba todavía la entrega automática de un próximo pago sin intervención
del panel. El 502 histórico sigue sin causa determinada. No declarar producción
lista ni renovación comercial completa por esta prueba.
Al terminar se cerraron únicamente los procesos del receptor/gateway de esta
sesión y su ngrok. La excepción era exclusiva del proceso, no se habilitó en .env.

### Nueva prueba de entrega automática autorizada (27/10 19:36 Chile)

El usuario confirmó una renovación de prueba para mp_prueba_local. Receptor
PID 15540 y gateway PID 10744 iniciados 19:35:38 por 90 minutos; ngrok PID 17800.
URL actual: https://0799-186-104-109-164.ngrok-free.app. Logs temporales con
sufijo 20261027-193538. Receptor con comprador autorizado 3081058526 y principal
local 3, excepción únicamente dentro del proceso. Salud pública 200, /admin/ 404,
firma inválida 401 comprobados. Cierre previsto aproximadamente 21:06 Chile.

Se creó Payment 2 por CLP 50.000, pending, expected_due_at
2026-11-26T23:30:08Z. Preferencia 3081058524-181f836c-c733-4b42-bb20-489263116ab1.
Las tres suscripciones se compararon antes/después y permanecen idénticas.
La preferencia incluye la URL nueva mediante override limitado a su creación;
.env no fue modificado. Reutilizar Payment 2; no crear otra orden.
Pendiente: usuario actualiza URL productiva en el panel de la aplicación del
vendedor de prueba y completa este NUEVO checkout como comprador de prueba.
No usar simulador/reenvío manual: se desea observar la entrega automática.
Si se aplica, fecha_fin esperada 2026-12-26T23:30:08Z, no desde la fecha del pago.

### Pausa solicitada al final del 27/10

El usuario no pulsó Pagar: el botón permaneció gris incluso al elegir otra
tarjeta de prueba. No se determinó la causa del bloqueo del checkout. Se pide
continuar mañana. Se cerraron el receptor, gateway y ngrok de esta sesión.
No abrir servicios ni crear nuevas órdenes hasta que el usuario retome.
Payment 2 estaba pending y sin notificación recibida en la última comprobación.
Al retomar consultar primero su estado, vigencia y posibles pagos en el proveedor
antes de reintentar o reemplazar la preferencia; no inferir fallo solo del botón.
La preferencia vence 28/10 a las 19:36 Chile; la URL de notificación temporal
ya no está activa. Actualizar/verificar las URLs antes de intentar el pago.
La prueba de entrega automática continúa pendiente; la activación y repetición
mediante el simulador sí fueron verificadas con Payment 1.

### Entrega automática completada (29/10/2026)

Para la prueba final se abrió un receptor local restringido y un túnel temporal,
se configuró la URL vigente en Webhooks de la aplicación del vendedor de prueba,
y se creó Payment 3 para mp_prueba_local. La operación 185721910867 fue aprobada
por Mercado Pago. El proveedor confirmó importes CLP 50.000, vendedor de prueba
3081058524, comprador autorizado 3081058526 y la referencia de Payment 3.

La notificación automática llegó sin simulador: gateway y receptor registraron
respuesta HTTP 200 a las 23:36:52 UTC. BINTRACK aplicó una sola PaymentAttempt,
marcó Payment 3 como approved y renovó el principal de prueba hasta
2027-01-26T23:30:08Z. La configuración global sigue con TEST_ENABLED=false;
la excepción de cuentas de prueba solo existió dentro del receptor temporal.
Al terminar se cerraron receptor, gateway y ngrok. Esta prueba completa valida
el recorrido automático local, pero no habilita producción ni pagos reales.
