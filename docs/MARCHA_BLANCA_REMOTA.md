# Marcha blanca remota

## Objetivo

Preparar BinTrack para una marcha blanca con un usuario de confianza fuera de la red local.

La marcha blanca busca validar:

- flujo real de uso;
- claridad de pantallas;
- errores técnicos;
- datos que faltan;
- reportes necesarios;
- puntos confusos antes de producción formal.

## Alcance inicial

La marcha blanca será controlada y con un solo usuario piloto.

No se considera todavía:

- publicación en Play Store;
- pagos reales obligatorios;
- bloqueo fuerte por suscripción;
- módulo de reenvasado;
- módulo de gastos operativos;
- reportes avanzados semanales;
- múltiples empresas o multiusuario avanzado.

## Estado actual del sistema

### Backend

El backend ya está preparado parcialmente para despliegue remoto:

- usa PostgreSQL;
- carga configuración desde `.env`;
- permite configurar `DEBUG`;
- permite configurar `ALLOWED_HOSTS`;
- permite configurar `CSRF_TRUSTED_ORIGINS`;
- tiene `STATIC_ROOT` para `collectstatic`;
- tiene flags HTTPS configurables por variables;
- tiene JWT para autenticación;
- tiene modelo base de suscripciones;
- pago aprobado activa o renueva suscripción.

### App Flutter

La app ya puede apuntar a un backend remoto usando:

```powershell
--dart-define=API_HOST=https://URL_DEL_BACKEND


Ejemplo:
flutter build apk --release --dart-define=API_HOST=https://api-bintrack.ejemplo.com
Requisito clave
Para marcha blanca remota real, el backend debe estar disponible 24/7.
No basta con usar python manage.py runserver en el equipo local si el usuario probará fuera de horario o fuera de la red WiFi.
Opciones de infraestructura
Opción A: Tailscale o VPN privada
Útil para pruebas cortas y controladas.
Ventajas:
no expone el backend públicamente;
no requiere dominio;
relativamente seguro.
Desventajas:
el equipo backend debe estar encendido;
Django debe estar corriendo;
el usuario debe instalar/configurar la VPN;
no sirve si el usuario probará libremente durante varios días.
Opción B: Servidor remoto con HTTPS
Recomendado para marcha blanca de varios días.
Ventajas:
disponible 24/7;
el usuario no necesita VPN;
se parece más a producción real;
permite probar desde cualquier internet.
Desventajas:
requiere hosting;
requiere configurar variables de entorno;
requiere base PostgreSQL remota;
requiere HTTPS;
requiere cuidar seguridad y backups.
Recomendación
Para un usuario piloto remoto que probará durante varios días, usar servidor remoto con HTTPS.
Tailscale puede servir solo como prueba previa muy controlada.
Variables de entorno necesarias
Ejemplo de variables para servidor:
DJANGO_SECRET_KEY=CAMBIAR_POR_UNA_CLAVE_SEGURA
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=api-bintrack.ejemplo.com

DJANGO_CORS_ALLOW_ALL=False
DJANGO_CORS_ALLOWED_ORIGINS=
DJANGO_CSRF_TRUSTED_ORIGINS=https://api-bintrack.ejemplo.com

DJANGO_SECURE_SSL_REDIRECT=False
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True

DB_NAME=bintrack
DB_USER=bintrack_user
DB_PASSWORD=CAMBIAR_PASSWORD
DB_HOST=HOST_POSTGRES
DB_PORT=5432

MERCADOPAGO_ENV=sandbox
MERCADOPAGO_ACCESS_TOKEN=
MERCADOPAGO_PUBLIC_KEY=
MERCADOPAGO_NOTIFICATION_URL=
MERCADOPAGO_SUCCESS_URL=
MERCADOPAGO_FAILURE_URL=
MERCADOPAGO_PENDING_URL=
Nota: DJANGO_SECURE_SSL_REDIRECT puede quedar en False si el proveedor de hosting ya maneja HTTPS y redirección.
Comandos base de servidor
Instalar dependencias:
pip install -r requirements.txt
Aplicar migraciones:
python manage.py migrate
Recolectar estáticos:
python manage.py collectstatic --noinput
Ejecutar con WSGI:
gunicorn backend.wsgi:application
No usar runserver en producción.
Preparación de datos
Antes de entregar al usuario piloto:
crear usuario piloto;
activar suscripción;
definir si la base parte vacía o con datos de ejemplo;
respaldar base de datos;
registrar fecha de inicio de marcha blanca.
APK de marcha blanca
Compilar APK release apuntando al backend remoto:
flutter build apk --release --dart-define=API_HOST=https://URL_DEL_BACKEND
Archivo generado:
build/app/outputs/flutter-apk/app-release.apk
Checklist funcional para usuario piloto
El usuario debe probar:
Iniciar sesión.
Ver estado de suscripción en Home.
Revisar guía de usuario.
Crear cliente.
Crear tipo de envase.
Registrar entrada de envases.
Crear producto.
Crear presentación.
Cargar stock inicial.
Crear venta.
Confirmar venta.
Registrar pago.
Generar comprobante si corresponde.
Revisar inventario.
Revisar balance de envases.
Reportar dudas, errores o pasos confusos.
Feedback esperado
Solicitar al usuario piloto anotar:
qué no entendió;
qué texto le confundió;
qué operación no pudo completar;
qué dato esperaba ver y no apareció;
qué pantalla fue lenta o incómoda;
errores visibles;
casos reales que la app aún no cubre.
Pendientes después de marcha blanca
Según feedback, evaluar:
bloqueo suave por suscripción;
pagos reales;
reenvasado de productos;
gastos operativos;
reportes semanales;
mejoras de inventario;
producción formal con dominio definitivo;
publicación en Play Store.