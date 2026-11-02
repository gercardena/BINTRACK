# Contexto operativo de BINTRACK

Este documento resume las decisiones durables del proyecto. No guardar aquí
contraseñas, tokens, URL con credenciales ni información personal de clientes.

## Repositorios

- Backend Django: `C:\proyectos\BINTRACK`.
- Aplicación Flutter: `C:\proyectos\bintrack_app`.
- Ambos repositorios se publican desde la rama `main`.

## Entornos

| Entorno | Uso | Datos |
| --- | --- | --- |
| Local | Desarrollo y pruebas con cuentas de prueba | Base de datos local |
| Render | Producción | Datos reales autorizados |

No mezclar cuentas de prueba ni datos ficticios con producción. Antes de una
migración de datos, respaldar y revisar la información autorizada.

## Producción

- Servicio web Render: `bintrack-backend`.
- Base de datos Render: `bintrack-db`.
- Región: Ohio (US East).
- URL de salud: `https://bintrack-backend.onrender.com/healthz/`.
- La rama `main` activa despliegues automáticos.
- Las variables de producción deben mantener HTTPS, cookies seguras y
  `DJANGO_SECURE_PROXY_SSL_HEADER=true`.

## Usuarios y suscripciones

- El alta de negocios es administrada; no hay registro público.
- Sin período activo, la cuenta queda en modo de solo lectura.
- El titular administra usuarios y suscripción. Los secundarios comparten la
  operación, pero no administran pagos.
- Planes actuales: titular; titular + 1 secundario; titular + 2 secundarios.
- El precio se calcula en el servidor para el siguiente ciclo. No hay cobro
  prorrateado al agregar un secundario.
- Las activaciones administrativas de marcha blanca deben quedar auditadas y
  ser autorizadas explícitamente.

## Pagos

- Mercado Pago de producción aún no está habilitado.
- El checkout de pruebas es opt-in y debe permanecer deshabilitado por defecto
  fuera de pruebas controladas.
- Nunca usar una redirección del navegador como prueba de pago: la confirmación
  debe venir de un webhook validado y ser idempotente.

## Cómo ejecutar localmente

Backend:

```powershell
cd C:\proyectos\BINTRACK
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Flutter en navegador, conectado al backend local:

```powershell
cd C:\proyectos\bintrack_app
$env:CHROME_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"
flutter run -d chrome --dart-define="API_HOST=http://127.0.0.1:8000"
```

## Pendientes

1. Configurar un proyecto Codex que incluya ambos repositorios.
2. Resolver la conectividad DNS/Wi-Fi del teléfono de pruebas hacia Render.
3. Preparar y validar una versión de escritorio Windows antes de distribuirla.
4. Diseñar, revisar y habilitar el checkout de Mercado Pago productivo.
