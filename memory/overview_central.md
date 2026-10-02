# Central Disruptivos: la central de control de los sitios de la agencia

> **Borrador pendiente de revisión.** Este documento se ha redactado a partir de los títulos de las 11 tareas históricas importadas; conviene que alguien del equipo lo complete y corrija antes de darlo por bueno.

## Resumen ejecutivo

Central Disruptivos es la aplicación interna desde la que la agencia supervisa los sitios web de sus clientes. Reúne en un solo lugar el inventario de sitios, los usuarios que pueden acceder, un sistema de escaneo y comprobaciones externas, la gestión de alertas y las notificaciones por email y n8n. Fue también la cuna de Cronos: el módulo de registro de créditos y tiempos nació dentro de ella antes de independizarse.

## Qué hemos construido

**Acceso y seguridad.** Login con Google, segundo factor (2FA) obligatorio con autoservicio de reconfiguración mediante código de recuperación, clave manual y enlace `otpauth`, y auditoría de acciones. Se resolvieron incidencias como la clave del QR que cambiaba en cada carga y bloqueaba la cuenta.

**Inventario y panel.** API de ingesta de datos, integración con los sitios, panel general, detalle por sitio y banner que recuerda activar el 2FA.

**Monitorización.** Escaneo bajo demanda, comprobaciones externas, gestión de alertas y la posibilidad de marcar incidencias como revisadas.

**Notificaciones y continuidad.** Avisos por email y por n8n, *dead-man switch* para detectar sitios que dejan de reportar, exportación a CSV y resumen semanal.

**Conector WordPress.** Plugin «Disruptivos Connector» descargable en ZIP que enlaza cada WordPress con la central; se corrigió un 403 al llamar a un endpoint interno y se añadieron una sonda y el botón «Probar conexión».

**Cronos (origen).** Registro de créditos y tiempos de los agentes IA, posteriormente trasladado a proyecto independiente con exportación de datos.

## Cómo lo hemos hecho

El desarrollo se organizó por fases (P1 a P7) ejecutadas con el agente de Emergent en pocas sesiones intensas: un MVP de acceso y gestión en la primera, la ingesta y el panel en la segunda y tercera, el escaneo y las alertas en la cuarta y quinta, y las notificaciones, la exportación y el resumen semanal en las dos últimas. Entre medias se atendieron consultas puntuales y correcciones derivadas del uso real, sobre todo en torno al 2FA y al plugin de WordPress.

_Completa aquí las decisiones técnicas, el stack y las lecciones aprendidas._

## Próximos pasos

- Revisar y completar este documento con el equipo.
- Cuadrar las 11 tareas históricas (siguen en estado estimado) con el extracto real de esas fechas.
