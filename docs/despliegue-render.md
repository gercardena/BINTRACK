# Despliegue inicial en Render

Este repositorio incluye `render.yaml` para crear los recursos productivos de
BINTRACK desde la rama `main`:

- Servicio web: `bintrack-backend` (`0.5c-512mb`).
- PostgreSQL: `bintrack-db` (`0.1c-256mb`, disco inicial de 1 GB).
- Comprobación de salud: `GET /healthz/` responde `200` con
  `{"status": "ok"}`.
- Las migraciones se ejecutan antes de cada despliegue exitoso.

## Qué no realiza este archivo

El archivo no copia datos locales, no habilita Mercado Pago productivo y no
crea usuarios administrativos. Al crear los recursos, la base de datos parte
vacía. Antes de apuntar el APK a Render se debe:

1. Respaldar la base local actual.
2. Preparar y revisar una exportación que conserve únicamente los datos reales
   autorizados para producción.
3. Excluir a Gerson y las cuentas de prueba de esa exportación.
4. Restaurar la copia aprobada en `bintrack-db`.
5. Crear un administrador de producción y comprobar el acceso.
6. Construir un APK de producción con la URL pública de Render.

## Alta en Render

1. En Render, crear un Blueprint desde el repositorio `BINTRACK` y elegir la
   rama `main`.
2. Revisar que se muestren exactamente `bintrack-backend` y `bintrack-db` con los
   planes indicados en `render.yaml`.
3. Confirmar el cargo mostrado por Render antes de crear los recursos.
4. Tras el primer despliegue, abrir `https://<subdominio>.onrender.com/healthz/`
   y comprobar que devuelva `{"status": "ok"}`.

Las credenciales de Mercado Pago de producción se agregarán sólo cuando el
checkout productivo esté listo y revisado.
