# Auth-Gated App Testing Playbook (Emergent Google Auth)

Cookie name: `session_token` (httpOnly, secure, SameSite=None). Backend also accepts `Authorization: Bearer <session_token>`.
Allowed domain: `@disruptivos.com`. Admins: `ADMIN_EMAILS` env (fran.gomez@disruptivos.com).

## Step 1: Create test user & session
```
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({ user_id: userId, email: 'fran.gomez@disruptivos.com', name: 'Fran Gómez', picture: '', created_at: new Date().toISOString() });
db.user_sessions.insertOne({ user_id: userId, session_token: sessionToken, expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(), created_at: new Date().toISOString() });
print('Session token: ' + sessionToken);
"
```
For a viewer, use an email like `viewer.test@disruptivos.com` (not in ADMIN_EMAILS).

## Step 2: Backend
```
curl "$URL/api/auth/me" -H "Authorization: Bearer TOKEN"
curl "$URL/api/cronos/entries" -H "Authorization: Bearer TOKEN"
```

## Step 3: Browser (Playwright)
```
await page.context.add_cookies([{"name":"session_token","value":"TOKEN","domain":"<host>","path":"/","httpOnly":true,"secure":true,"sameSite":"None"}])
await page.goto(URL)
```

## Cleanup
```
mongosh --eval "use('test_database'); db.user_sessions.deleteMany({session_token: /test_session/}); db.users.deleteMany({user_id: /test-user-/});"
```
