# Cronos Disruptivos · Instrucciones de uso

> App interna de Disruptivos para registrar y analizar el **tiempo, los mensajes y los créditos** que consumen los agentes de IA (Emergent) en cada tarea, y cuadrarlos con el extracto real. Este documento se actualiza con cada iteración.

## 1. Acceso y roles
- Entra con tu cuenta de Google **@disruptivos.com** (cualquier otro dominio se rechaza).
- **viewer** (por defecto): ve todo y registra/edita **sus propias** tareas y documentos de la wiki.
- **admin** (`ADMIN_EMAILS`): además edita cualquier tarea, cuadra extractos, gestiona Ajustes y proyectos.
- La sesión dura 7 días en una cookie segura. Las acciones sensibles quedan en la auditoría (Ajustes).

## 2. Registrar una tarea (Registro)
La forma más rápida es pegar la línea que el agente escribe al cerrar cada tarea en **Alta rápida**:

```
#cronos | título | tipo | fase | minutos | mensajes | créditos [| proyecto [| modelo]]
```

- **tipo**: `desarrollo`, `corrección`, `consulta`, `pruebas` (acepta variantes: fix, bug, dev, test…).
- **fase**: `P1`…`P7` u `otra`.
- Las cifras admiten `min`, `msg`, `cr`, comas decimales y separadores de miles (`1.234,5`).
- **modelo** (opcional): el modelo de IA usado (Claude Fable 5.1, GPT-5…). La lista se gestiona en Ajustes.

Tras «Analizar» se abre el formulario precargado: revisa fecha, usuario (los admins pueden asignarla a otra persona) y guarda. También puedes crear tareas con **Nueva** o editarlas/borrarlas desde la tabla (solo las tuyas si eres viewer).

Cada tarea nace con origen **estimado**. Exporta a CSV con el botón **CSV** (respeta los filtros).

## 3. Panel de costes
- **KPIs**: créditos, coste en € (precio por crédito de Ajustes), horas, tareas, mensajes.
- **Presupuesto mensual**: consumido vs presupuesto, proyección a fin de mes. Al cruzar el 80 % y el 100 % aparece un banner y se envía un email a los admins (una vez por mes).
- **Consumo por día**: créditos (área) + minutos y mensajes (líneas); pulsa en la leyenda para ocultar series.
- **Desgloses**: por tipo, fase (con topes y aviso «excedido»), origen, **modelo** y **usuario**.
- **Comparativa mensual**, **top tareas** y **tarjetas de proyecto** con semáforo (verde < 70 %, ámbar 70–100 %, rojo > 100 %).
- Los filtros (proyecto, tipo, fase, origen, usuario, modelo, fechas) afectan a todo el panel.

## 4. Equipo (consumo por usuario)
Tabla con cada persona del workspace: tareas, créditos, €, horas, mensajes, consumo del mes, modelo más usado y última actividad. Pulsa una fila para ver su registro filtrado.

## 5. Cuadrar con el extracto real
1. Pega el texto del extracto de Emergent o **sube el CSV** (arrastrar también vale).
2. Se detectan fechas (`AAAA-MM-DD` o `DD/MM/AAAA`) y créditos; las horas tipo 12:30 se ignoran.
3. Revisa la vista previa por día (real vs estimado, diferencia coloreada) y desmarca los días que no quieras aplicar.
4. **Aplicar cuadre** (admin): el gasto real se reparte proporcionalmente entre las tareas del día, que pasan a **confirmado** conservando su estimación original. Si el día no tiene tareas se crea una entrada «Sin asignar» (**importado**).
5. El **historial de cuadres** muestra qué días están ya cuadrados, con qué cifra y quién lo hizo.

## 6. Wiki de iteraciones
- La Wiki se abre en **Documento general**: por cada proyecto, un **documento global** estilo post (resumen ejecutivo, qué hemos construido por áreas, cómo lo hemos hecho, próximos pasos) con las cifras del proyecto en vivo (tareas, horas, créditos, €) y un índice lateral. Las iteraciones y fichas individuales quedan plegadas tras «Ver iteraciones y fichas»; desde el índice puedes saltar a una concreta.
- El documento global lo mantiene el agente al cerrar cada iteración y cualquier usuario puede editarlo (Markdown con vista previa, estado «borrador pendiente de revisión» / «revisado», historial de 10 versiones). «Regenerar con IA» lo sintetiza a partir de todas las fichas del proyecto (consume créditos) y lo deja en el editor para revisarlo antes de guardar.
- La pestaña **Fichas** muestra las tarjetas sueltas (con filtro por etiqueta) para consultar un documento concreto.
- Cada mejora de la app queda documentada en la **Wiki** (el agente crea la entrada al cerrar la tarea, origen «agente»).
- Las tareas **importadas** de otras apps (p. ej. el histórico de Central Disruptivos) generan automáticamente su documento (origen «importado») con la ficha de la tarea y una sección «Qué se ha hecho» pendiente de completar. `POST /api/cronos/import` admite además una lista `wiki: [...]` para traer la documentación ya escrita; y `POST /api/cronos/wiki/backfill` (admin) crea los documentos que falten.
- Desde el Registro, el icono de libro de cada fila abre su documento en la wiki.
- Cualquier usuario puede **crear** documentos manuales, **editar** los suyos (los admins, todos) y etiquetarlos. Se guarda un historial de las últimas 10 versiones.
- **Documentar con IA**: elige una tarea del registro o describe lo que has hecho y se genera un borrador en Markdown (consume créditos de la clave universal de Emergent) que puedes revisar antes de guardar.
- Búsqueda por texto, filtro por proyecto y por etiqueta.

## 7. Ajustes (admin)
- **€ por crédito** y **presupuesto mensual**.
- **Topes por fase** (P1…P7, otra).
- **Modelos de IA** disponibles en los formularios.
- **Proyectos**: objetivos de créditos mensual/total, color, archivar.
- **Recordatorio semanal**: cada lunes 08:00 (Madrid) se envía por email el resumen de la semana anterior; «Enviar ahora» lo lanza al momento.
- **Auditoría**: últimas acciones (quién, qué, cuándo, IP).

## 8. Convención con el agente
Al cerrar cada tarea de este proyecto, el agente:
1. Da de alta la tarea en el Registro (proyecto «Cronos Disruptivos», modelo en uso).
2. Crea la entrada correspondiente en la Wiki.
3. Cierra su respuesta con la línea `#cronos | … | Cronos Disruptivos | <modelo>` por si quieres pegarla a mano.

## 9. Sincronización con otras apps (Central Disruptivos, etc.)
Cronos **no ve** automáticamente lo que ocurre en otras apps: solo importa lo que esas apps exponen. Para sincronizar:
1. En la otra app debe existir una API que devuelva sus datos de Cronos: idealmente `GET /api/cronos/export.json` → `{ entries, statements, wiki }`; si no, `GET /api/cronos/entries` (+ `/statements`, `/wiki`). Debe aceptar un token estático (`Authorization: Bearer <token>` o `X-API-Key`).
2. En **Ajustes → Sincronización** añade la fuente: nombre, URL base (https), token y, opcionalmente, el proyecto a forzar y el usuario por defecto.
3. Pulsa **Actualizar** en el panel (o espera al cron diario de las 07:30). La importación es idempotente por `id`: lo nuevo se añade, lo existente se actualiza y nada se duplica. El resultado por fuente se ve en Ajustes y al pasar el ratón por «última sync».

Cronos también expone su propio `GET /api/cronos/export.json` para que otras apps puedan leer sus datos.

## Historial de cambios de este documento
- 2026-10-06 · v2: sincronización con otras apps (sección 9), documento global por proyecto en la Wiki.
- 2026-10-01 · v1: primera versión (Fase 1 + Fase 2, gráfica multi-serie, CSV, comparativa mensual, topes por fase, usuarios, modelos, wiki).
