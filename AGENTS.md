# BINTRACK backend

- Este repositorio contiene el backend Django. La aplicación Flutter vive en
  `C:\proyectos\bintrack_app`.
- Nunca incluir secretos, tokens, contraseñas, archivos `.env` ni copias de
  bases de datos en Git o documentación.
- Ejecutar comprobaciones proporcionadas por Django antes de publicar cambios.
- La producción se despliega automáticamente desde la rama `main` en Render.
- Mantener los pagos de Mercado Pago en modo seguro: no habilitar checkout
  productivo sin una solicitud explícita y una prueba completa.
- Consultar `docs/CONTEXTO_BINTRACK.md` antes de cambios de infraestructura,
  suscripciones o despliegue.
