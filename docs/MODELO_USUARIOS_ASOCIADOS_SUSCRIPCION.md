# Modelo de usuarios asociados a una suscripción

## Estado

Documento de diseño inicial.

Este documento describe una evolución futura de BinTrack para permitir que un usuario titular de una suscripción pueda agregar otros usuarios autorizados para trabajar sobre sus mismos datos.

No corresponde a una implementación inmediata. Su objetivo es ordenar el modelo antes de modificar código o base de datos.

---

## 1. Idea principal

El modelo actual de BinTrack asocia los datos operativos directamente a un usuario.

Ejemplo actual:

```text
Usuario titular -> Clientes
Usuario titular -> Envases
Usuario titular -> Productos
Usuario titular -> Inventario
Usuario titular -> Ventas
Usuario titular -> Pagos
Usuario titular -> Comprobantes
Usuario titular -> Suscripción
La evolución propuesta mantiene esa idea base, pero permite agregar usuarios asociados a la misma suscripción.
Ejemplo futuro:
Usuario titular
- Tiene la suscripción
- Es dueño de los datos operativos

Usuarios asociados
- Tienen su propio usuario y contraseña
- Operan sobre los datos del titular
- Sus acciones quedan registradas con creado_por
Regla principal:
El usuario titular conserva la suscripción y los datos.
Los usuarios asociados operan sobre los datos del titular.
Cada acción relevante registra qué usuario la realizó.
2. Conceptos principales
Usuario titular
Es el usuario principal de la cuenta.
Representa a la persona que contrató o administra el plan.
El usuario titular:
- Tiene la suscripción activa o pendiente
- Es dueño operativo de los datos
- Puede operar todos los módulos
- Puede agregar o desactivar usuarios asociados
- Puede revisar quién realizó cada acción
En el modelo actual, este usuario ya existe.
Ejemplo:
Usuario titular: piloto_render
Suscripción: Plan Marcha Blanca
Usuario asociado
Es un usuario autorizado por el titular para trabajar sobre sus mismos datos.
El usuario asociado:
- Tiene su propio usuario y contraseña
- No tiene una suscripción propia
- Usa la suscripción del titular
- Trabaja sobre clientes, envases, productos, inventario, ventas y pagos del titular
- Sus acciones quedan registradas mediante creado_por
Ejemplo:
Titular: piloto_render

Usuarios asociados:
- bodega_turno_1
- ventas_turno_1
- encargado_bodega
UsuarioAsociado
Modelo sugerido para relacionar un usuario asociado con un usuario titular.
Campos sugeridos:
UsuarioAsociado
- titular
- usuario_asociado
- rol
- activo
- fecha_creacion
Ejemplo:
titular: piloto_render
usuario_asociado: bodega_turno_1
rol: usuario
activo: true
3. Regla operativa principal
Cuando un usuario entra a la app, el backend debe identificar cuál es el usuario titular operativo.
Si el usuario es titular:
titular_operativo = request.user
Si el usuario es asociado:
titular_operativo = usuario titular asociado
Entonces los datos se consultan usando el titular operativo.
Ejemplo:
titular = get_usuario_titular(request.user)

Client.objects.filter(usuario=titular)
Al crear datos:
serializer.save(
    usuario=titular,
    creado_por=request.user,
)
Esto permite conservar la estructura actual de la app y agregar trazabilidad.
4. Trazabilidad
La trazabilidad es uno de los objetivos principales de este modelo.
Los datos siguen perteneciendo al usuario titular, pero cada acción importante debe registrar quién la realizó.
Ejemplo:
Cliente.usuario = piloto_render
Cliente.creado_por = bodega_turno_1
Venta.usuario = piloto_render
Venta.creado_por = ventas_turno_1
MovimientoEnvase.usuario = piloto_render
MovimientoEnvase.creado_por = encargado_bodega
Esto permite que el titular revise la operación sin perder control de sus datos.
5. Roles sugeridos para la primera versión
Para la primera versión no se recomienda partir con permisos complejos.
La realidad operativa de muchas bodegas es flexible:
- A veces opera solo el dueño.
- A veces opera un encargado.
- A veces varias personas trabajan en la misma bodega.
- Todos necesitan registrar movimientos, ventas, pagos o stock según el momento.
Por eso, en la primera versión se recomienda usar solo dos niveles:
Titular
Usuario asociado
Titular
Puede operar todos los módulos y administrar usuarios asociados.
Permisos sugeridos:
- Ver todos los módulos
- Crear y editar clientes
- Crear y editar envases
- Registrar movimientos de envases
- Crear y editar productos
- Crear y editar presentaciones
- Cargar stock
- Crear y confirmar ventas
- Registrar pagos
- Generar comprobantes
- Ver inventario
- Ver balance de envases
- Ver reportes
- Administrar usuarios asociados
- Ver información de suscripción
Usuario asociado
Puede operar los módulos principales, pero no administra suscripción ni usuarios.
Permisos sugeridos:
- Ver módulos operativos
- Crear y editar clientes
- Crear y editar envases
- Registrar movimientos de envases
- Crear y editar productos
- Crear y editar presentaciones
- Cargar stock
- Crear y confirmar ventas
- Registrar pagos
- Generar comprobantes
- Ver inventario
- Ver balance de envases
- Ver reportes operativos
No debería poder:
- Administrar usuarios asociados
- Cambiar datos de suscripción
- Modificar información del plan
6. Roles futuros opcionales
Más adelante, solo si el mercado lo pide, se podrían agregar roles más específicos.
Ejemplos:
- Solo lectura
- Ventas
- Bodega
- Administrador financiero
Pero estos roles no son necesarios para la primera versión.
La prioridad inicial debe ser:
- varios usuarios por suscripción
- mismos datos compartidos
- trazabilidad de quién hizo cada acción
- administración simple de usuarios asociados
7. Datos que seguirían perteneciendo al titular
En esta primera evolución, los datos operativos seguirían usando el campo usuario actual.
Ese campo representaría al usuario titular.
Entidades actuales:
Clientes
Tipos de envase
Movimientos de envase
Productos
Presentaciones
Inventario
Ventas
Items de venta
Pagos
Comprobantes
Payments de suscripción
Gastos futuros
Compras futuras
Ejemplo:
Cliente.usuario = titular
Producto.usuario = titular
Venta.usuario = titular
Inventario.usuario = titular
Además, se recomienda agregar progresivamente el campo:
creado_por
en las entidades donde sea importante saber quién hizo la acción.
8. Entidades donde conviene registrar creado_por
Campos sugeridos:
Cliente
- usuario
- creado_por

BinType
- usuario
- creado_por

BinMovement
- usuario
- creado_por

Product
- usuario
- creado_por

ProductPresentation
- creado_por opcional

Inventory
- usuario
- creado_por opcional

Sale
- usuario
- creado_por

SaleItem
- creado_por opcional

Pago
- creado_por

Factura
- creado_por
No todos los campos deben agregarse al mismo tiempo. Se puede hacer por fases.
Prioridad inicial:
- Movimientos de envases
- Ventas
- Pagos
- Carga de stock
9. Suscripciones
La suscripción sigue perteneciendo al usuario titular.
Modelo actual:
Usuario titular -> suscripción
Modelo propuesto:
Usuario titular -> suscripción
Usuario asociado -> usa la suscripción del titular
Esto permite:
Una persona paga el plan.
Esa persona puede agregar usuarios asociados.
Todos trabajan sobre los mismos datos.
10. Seguridad
Reglas mínimas:
- Un usuario asociado solo puede ver datos del titular al que pertenece.
- Un usuario asociado no puede ver datos de otros titulares.
- Un usuario asociado inactivo no puede operar.
- El titular puede desactivar usuarios asociados.
- La suscripción se valida sobre el titular operativo.
- Cada acción relevante debe registrar qué usuario la realizó.
11. Función clave sugerida
Crear una utilidad central para resolver el titular operativo.
Ejemplo:
def get_usuario_titular(user):
    relacion = UsuarioAsociado.objects.filter(
        usuario_asociado=user,
        activo=True,
    ).select_related(
        "titular",
    ).first()

    if relacion:
        return relacion.titular

    return user
Uso en vistas:
titular = get_usuario_titular(request.user)
Antes:
Client.objects.filter(usuario=request.user)
Después:
Client.objects.filter(usuario=titular)
Antes:
serializer.save(usuario=request.user)
Después:
serializer.save(
    usuario=titular,
    creado_por=request.user,
)
12. Impacto en Flutter
La app podría mostrar información como:
Titular de la cuenta: piloto_render
Usuario actual: bodega_turno_1
Suscripción: Activa
En una primera etapa no es necesario mostrar demasiada información.
Módulos futuros:
- Usuarios asociados
- Agregar usuario asociado
- Desactivar usuario asociado
- Ver quién creó una venta o movimiento
13. Ventajas de este modelo
Ventajas principales:
- Menor cambio estructural que crear una entidad Bodega.
- Aprovecha la arquitectura actual.
- Mantiene los datos asociados al usuario titular.
- Permite varios usuarios por suscripción.
- Cada usuario tiene su propia contraseña.
- Permite desactivar usuarios asociados sin cambiar la clave del titular.
- Agrega trazabilidad real.
14. Limitaciones
Este modelo es una evolución práctica del sistema actual, pero tiene algunas limitaciones:
- Los datos siguen perteneciendo técnicamente al usuario titular.
- No modela múltiples bodegas independientes dentro de una misma cuenta.
- Si en el futuro se necesita multi-bodega real, habría que evolucionar nuevamente.
Para la necesidad actual, estas limitaciones son aceptables.
15. Fases recomendadas
Fase 1: Documentación
- Definir usuario titular
- Definir usuario asociado
- Definir trazabilidad
- Definir reglas de seguridad
Fase 2: Backend base
- Crear modelo UsuarioAsociado
- Crear utilidad get_usuario_titular
- Permitir que un titular tenga usuarios asociados
Fase 3: Ajustar filtros
- Cambiar filtros usuario=request.user por usuario=titular_operativo
- Aplicar primero en módulos simples
- Probar clientes
- Probar envases
- Probar productos
- Probar ventas
Fase 4: Trazabilidad
- Agregar creado_por en acciones prioritarias
- Registrar creado_por=request.user al crear movimientos, ventas y pagos
- Mostrar creado_por en pantallas relevantes
Fase 5: Administración de usuarios
- Crear usuarios asociados desde admin o app
- Activar/desactivar usuarios asociados
- Mostrar usuarios asociados al titular
Fase 6: Flutter
- Mostrar usuario actual
- Mostrar titular de la cuenta si corresponde
- Agregar pantalla de usuarios asociados
- Mostrar quién hizo movimientos relevantes
16. Decisión inicial recomendada
Para la marcha blanca actual:
1 usuario titular = 1 suscripción = 1 operador principal
Para producción inicial:
1 usuario titular = 1 suscripción = varios usuarios asociados
Primera versión multiusuario:
- El titular conserva la suscripción y los datos.
- Los usuarios asociados operan sobre los datos del titular.
- Todos pueden operar módulos principales.
- Solo el titular administra usuarios asociados y suscripción.
- Cada acción relevante registra creado_por=request.user.
Este diseño permite evolucionar BinTrack sin rehacer la aplicación desde cero y aprovechando la separación por usuario que ya existe actualmente.