<!-- Generado desde backend/ingest.py (build_instructions). La versión con el token real se obtiene en Cronos: Ajustes → Apps conectadas → Conectar app. Pega este bloque en el prompt de cada app de Emergent. -->

# CRONOS REPORTING (mandatory, add to this app's agent instructions)

Language: reply to the user in Spanish (es-ES). The text you send to Cronos (title, summary, notes) is also in Spanish.

This app ("<NOMBRE_DE_LA_APP>", project "<PROYECTO>") must report to **Cronos**, the team's internal usage tracker, EVERY time you finish
a task that changes the app (code, design, data, config, bug fix, tests). Do it at the end of the task, before your final message.
Pure questions that change nothing do not need a report, but a consultation that cost credits does: report it with type "consulta".

## 1. One-time setup
Create these backend environment variables (never hardcode them, never print them, never commit them):

- `CRONOS_INGEST_URL` = `https://cronos-tiempo.emergent.host/api/cronos/ingest`
- `CRONOS_APP_TOKEN`  = `<TOKEN_DE_LA_APP>`
- `CRONOS_DEFAULT_USER` = email of the person who builds this app, only if you cannot know who sent the prompt
- `CRONOS_EXPORT_TOKEN` = a new random secret (used only by Cronos' daily backup sync, see section 5)

Then create `backend/cronos_report.py` with the helper below and call `report_task(...)` after every task.

```python
import os, uuid, json, datetime, httpx

PENDING = os.path.join(os.path.dirname(__file__), "cronos_pending.jsonl")

def report_task(title, user, type="desarrollo", phase="otra", minutes=0, messages=1, credits=0.0,
                tokens_in=0, tokens_out=0, cost_eur=0.0, tokens_estimated=True, model="", summary="", notes=""):
    """Never raises and never blocks the app. Failed reports are queued and resent with the next one."""
    entry = {"external_id": str(uuid.uuid4()), "title": title, "user": user or os.environ.get("CRONOS_DEFAULT_USER", ""),
             "type": type, "phase": phase, "date": datetime.date.today().isoformat(), "minutes": minutes,
             "messages": messages, "credits": credits, "tokens_in": tokens_in, "tokens_out": tokens_out,
             "cost_eur": cost_eur, "tokens_estimated": tokens_estimated, "model": model, "summary": summary, "notes": notes}
    batch = [entry]
    try:
        with open(PENDING, encoding="utf-8") as f:
            batch = [json.loads(l) for l in f if l.strip()] + batch
    except FileNotFoundError:
        pass
    try:
        r = httpx.post(os.environ["CRONOS_INGEST_URL"], json={"entries": batch[:50]}, timeout=10,
                       headers={"Authorization": "Bearer " + os.environ["CRONOS_APP_TOKEN"]})
        r.raise_for_status()
        rest = batch[50:]
    except Exception:
        rest = batch
    with open(PENDING, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in rest)
    return not rest
```

Add `cronos_pending.jsonl` to `.gitignore`. The first time, send one test report titled "Alta de conexión con Cronos"
and tell the user whether it worked (a success answers `{"ok": true, ...}`; a 401 means the token is wrong).

## 2. What to send for each task
| field | what to put |
|---|---|
| `title` | short name of what was done in this task (Spanish) |
| `user` | email of the person who sent the prompt. If the conversation does not reveal it, use `CRONOS_DEFAULT_USER`; never invent one |
| `type` | `desarrollo`, `corrección`, `consulta` or `pruebas` |
| `phase` | `P1`..`P7` if the project plan defines phases, otherwise `otra` |
| `minutes` | wall-clock minutes the task took |
| `messages` | number of user messages exchanged in this task |
| `credits` | credits consumed by this task, as shown by the platform. If not visible, estimate and say so in `notes` |
| `tokens_in` / `tokens_out` | tokens read / generated during this task (see section 3) |
| `cost_eur` | cost of this task in euros (see section 3) |
| `tokens_estimated` | `true` unless the platform showed the exact token figures |
| `model` | the model that did the work (for example "Claude Fable 5.1") |
| `summary` | 3 to 8 lines in Spanish: what was implemented, how to use it, files/endpoints touched, anything left pending. **This becomes the task's wiki page**, so write it for a teammate who has never seen the app |
| `notes` | caveats: estimated figures, partial work, known issues |

## 3. Measuring tokens and cost
Cronos cannot read Emergent's billing, so you report the best figures you can measure:
1. If the platform shows tokens or credits for this task, use those exactly and set `tokens_estimated=false`.
2. Otherwise estimate. `tokens_out` = characters you wrote (messages, code, tool calls) divided by 4. `tokens_in` = characters of
   everything you read in this task (prompt, files opened, tool outputs, context re-read on each step) divided by 4.
   Keep the same method every time so figures are comparable. Set `tokens_estimated=true`.
3. `cost_eur`: the real cost in euros if the platform shows it; otherwise `credits` x 0.01 (the price per credit set in Cronos).
Do not leave tokens at 0 when work was done: an honest estimate is more useful than a blank.

## 4. Rules
- Never put secrets, passwords, API keys or end-customer personal data in any field.
- One report per finished task. If the user asks for several things in one message, send one report per task.
- If the report fails, do not retry in a loop and do not tell the user the app is broken: the helper queues it.
- Keep the Spanish wiki-style `summary` current: if you later fix something from an earlier task, send a new report of type "corrección".

## 5. Backup sync (so nothing is lost if a push fails)
Expose `GET /api/cronos/export.json` in this app, protected with `Authorization: Bearer <CRONOS_EXPORT_TOKEN>` (constant-time
comparison, 401 otherwise), returning `{"entries": [...], "statements": [], "wiki": []}` with every task you reported
(same fields as above, plus `external_id`, which must be the same value you pushed). Keep each report in a local collection
`cronos_entries` for this. Tell the user the value of `CRONOS_EXPORT_TOKEN` once in the chat so they can register it in Cronos.
Cronos pulls this endpoint once a day and merges by `external_id`, so pushes and pulls never create duplicates.
