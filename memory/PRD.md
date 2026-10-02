# Cronos Disruptivos — PRD

## Problema original
App web interna de Disruptivos para registrar y analizar tiempo, mensajes y créditos que consumen los agentes IA (Emergent) por tarea/proyecto y cuadrarlos con el extracto real. UI en es-ES, código/API en inglés.

## Usuarios
- **admin** (ADMIN_EMAILS, inicial fran.gomez@disruptivos.com): CRUD entradas, cuadrar, ajustes, proyectos, enviar resumen.
- **viewer**: cualquier otra cuenta @disruptivos.com, solo lectura.

## Arquitectura
- React 19 + Tailwind + shadcn + react-query + recharts · FastAPI + Motor · MongoDB.
- Auth: Emergent-managed Google OAuth, dominio restringido a @disruptivos.com, cookie httpOnly `session_token` (7 días), colecciones `users`, `user_sessions`, `audit_log`.
- Email: Emergent-managed Resend (`EMERGENT_EMAIL_KEY`, `EMAIL_FROM_NAME`) — no se usa RESEND_API_KEY propia.
- Crons de plataforma `.emergent/crons.yml`: `weekly-digest` lunes 08:00 Europe/Madrid → POST /api/cron/weekly-digest; `budget-check` diario 09:00 → POST /api/cron/budget-check (Bearer WEBHOOK_CRON_SECRET, idempotente por X-Webhook-Id en `cron_runs`).
- Backend: `server.py` (app, lifespan seed, cron), `auth.py`, `cronos.py` (rutas /api/cronos/*), `emailer.py`, `seed_data.json`.

## Colecciones
`cronos_entries`, `cronos_statements`, `cronos_projects`, `cronos_settings` (price_per_credit_eur=0.01, monthly_budget_credits=5000, alerts_sent{YYYY-MM:[80,100]}), `users`, `user_sessions`, `audit_log`, `cron_runs`.

## Implementado (2026-10-01)
- Fase 1 completa: meta, entries CRUD con validación, parse-line tolerante, stats, reconcile preview/apply proporcional + «Sin asignar», export.csv (BOM, coste_eur), import idempotente + seed automático con 11 entradas históricas.
- Fase 2 completa: € por crédito en KPIs/tabla/CSV; presupuesto mensual con barra, proyección y avisos 80%/100% (banner + email una vez por mes); proyectos con objetivos y semáforo; resumen semanal por email con botón «Enviar ahora»; auditoría visible en Ajustes.
- Páginas: /login, / (panel), /registro, /cuadrar, /ajustes (admin).
- Tests: iteration_1 → backend 44/44, frontend 100% flujos críticos.
- (2026-10-01) Gráfica diaria con series de minutos y mensajes (eje derecho, toggles). Cuadre desde CSV subido/arrastrado: detección de columnas fecha/créditos por cabecera con fallback al parser de texto; `format` en la respuesta de preview.
- (2026-10-02) Documento global por proyecto (`cronos_wiki_overview`, `GET/PUT /wiki-overview`, `POST /wiki-overview/generate`), `ProjectOverview.jsx`, iteraciones plegadas en `WikiGeneral.jsx`. Textos fuente en `/app/memory/overview_*.md`. vista continua por proyecto con índice (`WikiGeneral.jsx`, `GET /wiki?full=true`); fichas en pestaña secundaria. por tarea (`ensure_wiki_for_entry`, source `importado`), acepta lista `wiki`, endpoint admin `POST /wiki/backfill`; filtros `entry_id`/`project` en wiki; icono wiki por fila en Registro; `/wiki?entry=`. campos `user`/`model` en entradas, permisos por propietario (viewers crean/editan las suyas), página /equipo (`GET /users`), desgloses por modelo/usuario, filtros, CSV. Wiki (`cronos_wiki`, `wiki.py`): CRUD Markdown con historial, búsqueda, etiquetas, «Documentar con IA» (claude-sonnet-5-5 vía EMERGENT_LLM_KEY). Guía (/instrucciones) renderiza `/app/instrucciones.md`. Lista de modelos editable en Ajustes. Convención: el agente registra la tarea y crea la entrada wiki (source `agente`) al cerrar cada iteración, usando el token admin local `test_session_e1`. (`stats.monthly` con Δ% vs mes anterior), historial de cuadres en /cuadrar (GET /statements), topes de créditos por fase (`cronos_settings.phase_goals`, formulario en Ajustes, fases excedidas en rojo en el panel).

## Backlog
- P1: debounce en digest/send; paginación del registro si crece mucho.
- P2: gráfica de mensajes/minutos junto a créditos; notificaciones in-app de cuadre pendiente; exportar PDF.
- P2: dividir cronos.py en módulos cuando crezca.
