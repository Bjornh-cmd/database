# Integratie-prompt

> **Tip:** Open een database in het admin panel (http://localhost:5505) → tab **Integratie prompt**. Daar staat de volledige prompt al ingevuld met jouw API URL, username, tabellen en CREATE/API commands. Je kunt ook je projectbeschrijving invullen en direct kopieren.

Kopieer onderstaande prompt en plak die in Cursor/ChatGPT wanneer je dit database-platform wilt koppelen aan een andere app.

---

## Prompt (kopieer vanaf hier)

```
Integreer mijn app met een externe multi-tenant REST database-API.

## Database platform

- **Admin panel** (alleen voor beheer): http://localhost:5505
- **Database API** (voor mijn app): http://localhost:4392
- Alle tenant-databases delen hetzelfde API-adres, maar hebben elk een unieke username + password.
- Schema (tabellen/kolommen) wordt beheerd via het admin panel — mijn app praat alleen met de REST API.

## Authenticatie

1. Login eenmalig (of bij token expiry opnieuw):

POST http://localhost:4392/auth/login
Content-Type: application/json

{
  "username": "<DATABASE_USERNAME>",
  "password": "<DATABASE_PASSWORD>"
}

Response:
{
  "access_token": "<JWT>",
  "token_type": "bearer",
  "database": { "id": 1, "name": "...", "slug": "..." }
}

2. Alle volgende requests: Authorization: Bearer <JWT>

3. Token checken:
GET http://localhost:4392/auth/me

## Beschikbare endpoints (na login)

| Method | Endpoint | Beschrijving |
|--------|----------|--------------|
| GET | /tables | Alle tabellen + kolomschema |
| GET | /{table} | Lijst rijen (?limit=50&offset=0&sort=kolom) |
| GET | /{table}/{id} | Enkele rij op primary key |
| POST | /{table} | Nieuwe rij (JSON body = kolom→waarde) |
| PATCH | /{table}/{id} | Rij updaten (partial body) |
| DELETE | /{table}/{id} | Rij verwijderen |

## Kolomtypes

text, integer, float, boolean, datetime, json

- Integer primary keys krijgen auto-increment bij POST (hoef je niet mee te sturen).
- Primary key kan niet geüpdatet worden via PATCH.

## Foutcodes

- 401 — verkeerde login of verlopen/ontbrekend token → opnieuw inloggen
- 404 — tabel of rij niet gevonden
- 422 — validatiefout (verkeerd type, ontbrekende verplichte kolom)

## Wat je moet bouwen

1. Een herbruikbare API-client module/service met:
   - login(username, password) → sla token op (memory/localStorage/env)
   - authenticated fetch wrapper met Bearer header
   - auto retry bij 401 (opnieuw login indien credentials beschikbaar)
   - typed helpers: listTables(), listRows(table), getRow(table, id), createRow(table, data), updateRow(table, id, data), deleteRow(table, id)

2. Environment variables:
   - DB_API_URL=http://localhost:4392
   - DB_USERNAME=<tenant username uit admin>
   - DB_PASSWORD=<tenant password uit admin>

3. Vervang hardcoded/mock data door echte API calls naar de juiste tabellen.

4. Toon duidelijke foutmeldingen bij netwerk- of validatiefouten.

## Voorbeeld flow (JavaScript)

const BASE = process.env.DB_API_URL;

async function login() {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: DB_USERNAME, password: DB_PASSWORD }),
  });
  if (!res.ok) throw new Error('Database login failed');
  const { access_token } = await res.json();
  return access_token;
}

async function api(token, path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  if (res.status === 204) return null;
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Gebruik:
// const token = await login();
// const products = await api(token, '/products');
// await api(token, '/products', { method: 'POST', body: JSON.stringify({ name: 'Apple', price: 1.5 }) });

## Mijn project

[Beschrijf hier je project: framework, taal, welke tabellen je gebruikt, wat de app moet doen]

Voorbeeld:
- Next.js 14 app in TypeScript
- Tabellen: products (id, name, price), orders (id, product_id, quantity)
- Ik wil een productenlijst pagina en formulier om producten toe te voegen
- Gebruik DB_API_URL, DB_USERNAME, DB_PASSWORD uit .env.local
```

---

## Korte variant (snelle integratie)

```
Koppel mijn app aan REST database API op http://localhost:4392.

Login: POST /auth/login met { username, password } → Bearer token.
CRUD: GET/POST/PATCH/DELETE /{table} en /{table}/{id}, header Authorization: Bearer <token>.
Schema: GET /tables.

Maak een API-client module, gebruik env vars DB_API_URL, DB_USERNAME, DB_PASSWORD, en vervang mock data door echte calls.

Mijn stack: [VUL IN]
Mijn tabellen: [VUL IN]
```

---

## Admin credentials (alleen voor beheer, niet in je app)

| Wat | Waarde |
|-----|--------|
| Admin URL | http://localhost:5505 |
| Default login | admin / changeme (zie `.env`) |

Database credentials voor je app maak je aan via het admin panel onder "Nieuwe database".
