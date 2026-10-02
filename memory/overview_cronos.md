# Cronos Disruptivos: el cuadro de mando del consumo de agentes IA

## Resumen ejecutivo

Cronos Disruptivos nació para responder a una pregunta sencilla que hasta ahora no teníamos forma de contestar con datos: **¿cuánto nos cuesta realmente cada tarea que delegamos en un agente de IA?** En Emergent el consumo se mide en créditos, y esos créditos se traducen en euros, pero el extracto de uso que nos devuelve la plataforma solo dice *cuánto* se gastó cada día, no *en qué*. Cronos cierra ese hueco: cada tarea que cerramos con el agente queda registrada con su tiempo, sus mensajes, sus créditos estimados, el proyecto, la fase, el modelo de IA utilizado y la persona que la hizo. Después, cuando llega el extracto real, lo cuadramos contra lo estimado y repartimos el gasto real entre las tareas del día. El resultado es un panel donde vemos de un vistazo qué proyectos, qué fases, qué tipos de trabajo, qué modelos y qué personas concentran el gasto, cuánto llevamos del presupuesto mensual y hacia dónde vamos.

La app es interna, con acceso restringido a cuentas **@disruptivos.com** mediante Google, y está pensada para ser rápida de usar: registrar una tarea cuesta pegar una línea.

## Qué hemos construido

**Registro de tareas.** El corazón de la app. Cada tarea tiene título, proyecto, tipo (desarrollo, corrección, consulta, pruebas), fase (P1–P7 u otra), fecha, minutos, mensajes, créditos, origen (estimado, confirmado o importado), usuario, modelo de IA y notas. La alta rápida interpreta la línea `#cronos | título | tipo | fase | minutos | mensajes | créditos | proyecto | modelo` que el agente escribe al terminar, tolerando variantes como «25 min», «1.234,5 cr» o «fix». La tabla es densa, filtrable por todos los campos y exportable a CSV con la columna de coste en euros.

**Panel de costes.** KPIs grandes (créditos, coste en €, horas, tareas, mensajes y ratios por tarea, por mensaje y por minuto), gráfica diaria con créditos, minutos y mensajes, desgloses por tipo, fase, origen, modelo y usuario, comparativa de cuánto gasto va a corregir errores frente a construir, comparativa mes a mes con variación porcentual, top de tareas más caras y tarjetas de proyecto con semáforo frente a su objetivo.

**Presupuesto y alertas.** Un presupuesto mensual global de créditos con barra de progreso, proyección a fin de mes según el ritmo diario y avisos automáticos al cruzar el 80 % y el 100 % (banner en la app y email a los administradores, una sola vez por mes). Además, topes de créditos por fase que se marcan en rojo cuando se superan, y objetivos por proyecto, mensuales o totales.

**Cuadre con el extracto real.** Pegas el texto del extracto de Emergent, o subes su CSV, y Cronos detecta fechas y cifras, agrupa el gasto real por día y lo compara con lo estimado. Al aplicar, reparte el gasto real proporcionalmente entre las tareas del día, conserva la estimación original y marca las tareas como confirmadas. Si un día no tiene tareas, crea una entrada «Sin asignar». Un historial muestra qué días están cuadrados, con qué cifra y quién lo hizo.

**Equipo.** Vista por persona del workspace: tareas, créditos, euros, horas, mensajes, consumo del mes, modelo más usado y última actividad. Cada usuario registra y edita sus propias tareas; los administradores pueden asignarlas y editarlo todo.

**Wiki y documentación.** Cada iteración del proyecto queda documentada en una wiki en Markdown con editor, vista previa, etiquetas, búsqueda e historial de versiones. Las tareas importadas de otros proyectos generan su ficha automáticamente. Un botón «Documentar con IA» redacta borradores a partir de una tarea o una descripción, y este mismo documento global puede regenerarse con IA a partir de todas las fichas. La guía de uso (`instrucciones.md`) se lee desde la propia app.

**Recordatorio semanal.** Cada lunes a las 08:00 (Madrid) un email resume la semana anterior: créditos y euros, horas, tareas, top 5, comparativa con la semana previa, estado del presupuesto y días pendientes de cuadrar.

## Cómo lo hemos hecho

Partimos de un módulo que ya existía dentro de Central Disruptivos y lo convertimos en producto propio con el stack estándar de la agencia: **React** con Tailwind y componentes shadcn en el frontend, **FastAPI** con Motor en el backend y **MongoDB** como base de datos. La primera iteración entregó de golpe las dos fases previstas (registro, estadísticas, cuadre, exportación e importación del histórico; y coste en euros, presupuesto, objetivos por proyecto y recordatorio semanal), con pruebas automatizadas end-to-end desde el primer día.

Tomamos algunas decisiones deliberadas. La autenticación se apoya en el Google gestionado por Emergent, con la restricción de dominio y los roles resueltos en el servidor a partir de la variable `ADMIN_EMAILS`, sin gestionar contraseñas. El email sale por el Resend gestionado por la plataforma, con una pasarela de seguridad que impide formularios, enlaces no HTTPS o peticiones de credenciales. Las tareas programadas no viven en un bucle dentro de la app, sino en los crons de la plataforma (`.emergent/crons.yml`), que llaman a endpoints protegidos por un secreto y son idempotentes.

En el cuadre apostamos por el **reparto proporcional**: si un día el extracto real suma 692,5 créditos y las tareas estimaban 690, cada tarea recibe su parte en proporción a lo que estimó, y la estimación original se guarda para poder medir después cuánto nos desviamos. El parser del extracto acepta texto libre o CSV detectando las columnas por su cabecera.

A partir de ahí fuimos iterando en pasos cortos, cada uno registrado en Cronos con su coste: gráfica multi-serie y CSV, comparativa mensual e historial de cuadres, topes por fase, logo e identidad, y finalmente el salto a multiusuario con campo de modelo, página de Equipo, wiki e instrucciones. La convención de trabajo con el agente se mantiene: al cerrar cada tarea registra su consumo, documenta la iteración en la wiki y actualiza la guía.

## Próximos pasos

- Completar la documentación de las fichas históricas con ayuda de la IA.
- Objetivos de créditos por usuario con aviso en Equipo.
- Aviso en el panel de los días que llevan más de una semana en estimado sin cuadrar.
- Edición de la guía desde la propia app y exportación del documento global a Markdown o PDF.
