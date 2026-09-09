# Modelo multiusuario por bodega

## Estado

Documento de diseño inicial.

Este documento describe una evolución futura de BinTrack para permitir que una misma bodega tenga varios usuarios trabajando sobre los mismos datos.

No corresponde a una implementación inmediata. Su objetivo es ordenar el modelo antes de modificar código o base de datos.

---

## 1. Idea principal

El modelo actual de BinTrack asocia los datos operativos directamente a un usuario.

Ejemplo actual:

```text
Usuario -> Clientes
Usuario -> Envases
Usuario -> Productos
Usuario -> Inventario
Usuario -> Ventas
El modelo futuro propone que los datos pertenezcan a una bodega, y que varios usuarios puedan trabajar dentro de esa misma bodega.
Ejemplo futuro:
Bodega -> Clientes
Bodega -> Envases
Bodega -> Productos
Bodega -> Inventario
Bodega -> Ventas
Bodega -> Pagos
Bodega -> Comprobantes

Usuario -> pertenece a una o más bodegas
Regla principal:
La bodega es dueña de los datos.
El usuario representa a la persona que realiza la acción.
2. Conceptos principales
Bodega
Representa la cuenta operativa principal dentro de BinTrack.
Una bodega puede ser una bodega física, un negocio, una unidad operativa o una cuenta comercial.
Campos sugeridos:
Bodega
- nombre
- rut opcional
- teléfono opcional
- dirección opcional
- plan
- suscripción activa
- fecha inicio de plan
- fecha fin de plan
- activa
- fecha creación
En la app se debe hablar siempre de “Bodega”, no de empresa, organización o workspace.
Usuario
Representa a una persona que puede iniciar sesión en BinTrack.
Campos actuales del usuario se pueden mantener:
Usuario
- username
- email
- password
- rut
- teléfono
- activo
El usuario ya no debería ser dueño directo de todos los datos operativos.
UsuarioBodega
Relación entre un usuario y una bodega.
Permite que una bodega tenga varios usuarios.
Campos sugeridos:
UsuarioBodega
- usuario
- bodega
- rol
- activo
- fecha creación
Ejemplo:
Bodega: San Pedro

Usuarios:
- dueño@bodega.cl -> Administrador de bodega
- bodega@bodega.cl -> Usuario de bodega
- ventas@bodega.cl -> Usuario de bodega
3. Roles sugeridos para la primera versión
Para el tipo de operación que busca BinTrack, no se recomienda partir con permisos demasiado restrictivos.
En muchas bodegas, la operación diaria queda a cargo de una o varias personas según el turno o la disponibilidad. A veces está solo el dueño, a veces está el encargado de bodega, y otras veces trabajan varias personas al mismo tiempo.
Por eso, en la primera versión multiusuario, todos los usuarios activos de una bodega deberían poder operar los módulos principales.
La diferencia más importante no será limitar qué módulo puede usar cada persona, sino registrar quién hizo cada movimiento.
Regla principal:
Todos los usuarios activos de una bodega pueden operar.
Cada acción relevante debe registrar qué usuario la realizó.
Administrador de bodega
Usuario responsable de la cuenta de la bodega.
Puede operar todos los módulos y además administrar aspectos generales de la bodega.
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
- Administrar usuarios de la bodega
- Ver información del plan o suscripción
Usuario de bodega
Usuario operativo de la bodega.
Puede trabajar normalmente en los módulos principales, pero no administra usuarios ni suscripción.
Permisos sugeridos:
- Ver todos los módulos operativos
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
- Administrar usuarios de la bodega
- Cambiar datos del plan
- Modificar información de suscripción
3.1 Roles futuros opcionales
Más adelante, solo si el mercado lo pide, se podrían agregar roles más específicos.
Ejemplos:
- Solo lectura
- Ventas
- Bodega
- Administrador financiero
Pero estos roles no son necesarios para la primera versión multiusuario.
La prioridad inicial debe ser:
- varios usuarios por bodega
- mismos datos compartidos
- trazabilidad de quién hizo cada acción
- administración simple de usuarios
4. Datos que deberían pertenecer a una bodega
En el modelo futuro, estas entidades deberían tener campo bodega:
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
Además, algunas entidades deberían conservar referencia al usuario que realizó la acción.
Ejemplo:
Movimiento de envase
- bodega
- creado_por
- cliente
- envase
- tipo_movimiento
- cantidad
Venta
- bodega
- creado_por
- cliente
- total
5. Suscripciones
La suscripción debería pertenecer a la bodega, no al usuario individual.
Modelo actual:
Usuario -> suscripción
Modelo futuro:
Bodega -> suscripción
Esto permite:
Una bodega paga un plan.
La bodega puede tener varios usuarios.
Los usuarios usan el acceso de esa bodega.
6. Migración desde el modelo actual
El modelo actual ya separa datos por usuario.
Para migrar al modelo por bodega se puede hacer lo siguiente:
Paso 1
Crear una bodega automática por cada usuario actual.
Ejemplo:
Usuario: gerson
Bodega creada: Bodega de gerson
Paso 2
Crear relación UsuarioBodega para cada usuario.
gerson -> Bodega de gerson -> Administrador de bodega
Paso 3
Mover los datos actuales del usuario a su bodega.
Ejemplo:
Clientes donde usuario = gerson
pasan a:
Clientes donde bodega = Bodega de gerson
Paso 4
Mantener el campo usuario temporalmente como referencia histórica o creado_por.
Paso 5
Actualizar filtros del backend.
Antes:
Client.objects.filter(usuario=request.user)
Después:
Client.objects.filter(bodega=bodega_actual)
7. Bodega activa
En una primera versión, cada usuario puede pertenecer a una sola bodega.
Más adelante se podría permitir que un usuario pertenezca a más de una bodega.
Para simplificar la primera implementación:
Un usuario inicia sesión.
El sistema identifica su bodega activa.
Todas las consultas usan esa bodega.
8. Reglas de seguridad
Reglas mínimas:
- Un usuario solo puede ver datos de las bodegas donde está activo.
- Un usuario no puede modificar datos de otra bodega.
- Los usuarios activos pueden operar los módulos principales.
- Solo el administrador puede gestionar usuarios y suscripción.
- Cada acción relevante debe registrar qué usuario la realizó.
- Los usuarios inactivos no pueden operar.
- La suscripción se valida a nivel de bodega.
9. Impacto en la app Flutter
La app debería mostrar información como:
Bodega actual: San Pedro
Rol: Administrador de bodega
Suscripción: Activa
En una primera etapa no es necesario mostrar selector de bodega si cada usuario pertenece a una sola.
Módulos futuros:
- Usuarios de la bodega
- Administración simple de usuarios
- Visualización de quién realizó cada movimiento
10. Trazabilidad
Uno de los objetivos principales del modelo multiusuario por bodega es que el dueño o administrador pueda revisar qué ocurrió en la operación.
La app debería permitir saber qué usuario realizó acciones relevantes.
Ejemplos:
Movimiento de envase creado por: bodega@bodega.cl
Venta confirmada por: ventas@bodega.cl
Pago registrado por: dueño@bodega.cl
Stock cargado por: operador@bodega.cl
Acciones relevantes a registrar:
- Creación o edición de clientes
- Creación o edición de envases
- Movimientos de envases
- Creación o edición de productos
- Creación o edición de presentaciones
- Carga o ajuste de stock
- Creación de ventas
- Confirmación de ventas
- Registro de pagos
- Generación de comprobantes
- Registro de gastos futuros
- Registro de compras futuras
11. Fases recomendadas
Fase 1: Diseño y documentación
- Definir modelo Bodega
- Definir usuarios de bodega
- Definir permisos simples
- Definir migración
Fase 2: Backend base
- Crear modelo Bodega
- Crear modelo UsuarioBodega
- Crear bodega automática para usuarios actuales
- Asociar suscripción a bodega
Fase 3: Migración de datos operativos
- Agregar campo bodega a entidades principales
- Migrar datos existentes
- Ajustar filtros backend
Fase 4: Trazabilidad
- Registrar creado_por en acciones relevantes
- Mostrar usuario responsable en movimientos, ventas y pagos
Fase 5: Permisos simples
- Usuario administrador de bodega
- Usuario de bodega
- Solo administrador gestiona usuarios y suscripción
- Ambos pueden operar módulos principales
Fase 6: Flutter
- Mostrar bodega actual
- Mostrar rol
- Agregar administración simple de usuarios de bodega
- Mostrar quién realizó movimientos relevantes
12. Decisión inicial recomendada
Para la marcha blanca actual:
1 bodega = 1 usuario principal
Para producción:
1 bodega = varios usuarios
Primera versión multiusuario:
- Todos los usuarios activos pueden operar
- Solo administrador gestiona usuarios y suscripción
- Cada acción relevante registra quién la realizó
Este diseño permite evolucionar BinTrack sin rehacer la aplicación desde cero y usando un lenguaje cercano al usuario real: bodega, usuarios de bodega y movimientos de bodega.git