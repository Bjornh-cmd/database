import json
from typing import Any

from shared.models import ColumnDefinition, ColumnType, Database, TableDefinition
from shared.tenant_engine import _column_sql


def format_create_table_sql(table: TableDefinition) -> str:
    cols_sql = ",\n  ".join(_column_sql(c) for c in table.columns)
    return f'CREATE TABLE "{table.name}" (\n  {cols_sql}\n);'


def _example_value(col: ColumnDefinition) -> Any:
    if col.is_primary_key and col.type == ColumnType.INTEGER.value:
        return None
    examples = {
        ColumnType.TEXT.value: "voorbeeld",
        ColumnType.INTEGER.value: 1,
        ColumnType.FLOAT.value: 9.99,
        ColumnType.BOOLEAN.value: True,
        ColumnType.DATETIME.value: "2026-06-16T12:00:00",
        ColumnType.JSON.value: {"key": "value"},
    }
    return examples.get(col.type, "voorbeeld")


def example_insert_body(table: TableDefinition) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for col in table.columns:
        if col.is_primary_key and col.type == ColumnType.INTEGER.value:
            continue
        body[col.name] = _example_value(col)
    return body


def build_table_api_examples(api_url: str, table: TableDefinition) -> dict[str, str]:
    insert_body = example_insert_body(table)
    pk_col = next(c for c in table.columns if c.is_primary_key)
    pk_example = 1 if pk_col.type == ColumnType.INTEGER.value else "id-waarde"

    insert_json = json.dumps(insert_body, indent=2, ensure_ascii=False)
    patch_json = json.dumps(
        {k: v for k, v in insert_body.items() if k in list(insert_body.keys())[:1]},
        indent=2,
        ensure_ascii=False,
    )

    return {
        "create_sql": format_create_table_sql(table),
        "list": f"GET {api_url}/{table.name}",
        "get_one": f"GET {api_url}/{table.name}/{pk_example}",
        "create": f"POST {api_url}/{table.name}\nContent-Type: application/json\n\n{insert_json}",
        "update": f"PATCH {api_url}/{table.name}/{pk_example}\nContent-Type: application/json\n\n{patch_json}",
        "delete": f"DELETE {api_url}/{table.name}/{pk_example}",
        "insert_body": insert_json,
    }


def _format_tables_summary(database: Database) -> str:
    if not database.tables:
        return "Geen tabellen — maak ze aan via admin panel of stuur kolommen mee in POST/PATCH."
    lines = []
    for table in database.tables:
        cols = ", ".join(f"{c.name} ({c.type})" for c in table.columns)
        lines.append(f"- **{table.name}**: {cols}")
    return "\n".join(lines)


def _format_table_commands_block(api_url: str, database: Database) -> str:
    if not database.tables:
        return ""
    blocks = []
    for table in database.tables:
        ex = build_table_api_examples(api_url, table)
        blocks.append(
            f"### Tabel `{table.name}`\n\n"
            f"CREATE TABLE:\n```sql\n{ex['create_sql']}\n```\n\n"
            f"Lijst: `{ex['list']}`\n\n"
            f"Insert:\n```http\n{ex['create']}\n```\n\n"
            f"Update: `{ex['update'].split(chr(10))[0]}`\n"
            f"Delete: `{ex['delete']}`\n"
        )
    return "\n".join(blocks)


def _js_client_example(api_url: str, username: str, password: str, tables: list[str]) -> str:
    table_list = ", ".join(f'"{t}"' for t in tables) or '"<table>"'
    return f"""const DB_API_URL = "{api_url}";

async function dbFetch(path, options = {{}}) {{
  const res = await fetch(`${{DB_API_URL}}${{path}}`, {{
    ...options,
    headers: {{
      "Content-Type": "application/json",
      ...options.headers,
    }},
  }});
  if (res.status === 204) return null;
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}}

// Credentials zitten in de URL: /api/{username}/<password>/
// Beschikbare tabellen: [{table_list}]
// Voorbeeld: await dbFetch("/products");
// Nieuwe kolommen in body worden automatisch aangemaakt (schema-less)
// Voorbeeld: await dbFetch("/products", {{ method: "POST", body: JSON.stringify({{ name: "test", price: 9.99 }}) }});"""


def build_integration_prompt(
    api_url: str,
    database: Database,
    password: str | None,
    admin_url: str | None = None,
) -> str:
    if not password:
        return (
            "Wachtwoord niet beschikbaar voor deze database.\n\n"
            "Ga naar tab Instellingen → vul een nieuw client wachtwoord in → Opslaan → "
            "open deze tab opnieuw. Daarna bevat de prompt alle credentials."
        )

    tables_summary = _format_tables_summary(database)
    table_commands = _format_table_commands_block(api_url, database)
    table_names = [t.name for t in database.tables]
    js_client = _js_client_example(api_url, database.username, password, table_names)

    table_names_str = ", ".join(f"`{n}`" for n in table_names) if table_names else "nog geen"
    admin_panel = admin_url or "http://localhost:5505/db"
    server_port = api_url.rsplit(":", 1)[-1].split("/", 1)[0]
    host_ip = api_url.split("://", 1)[1].rsplit(":", 1)[0]

    return f"""Koppel mijn huidige project aan onderstaande REST database-API. Gebruik EXACT deze credentials en configuratie — vraag mij NIET om API URL, IP, username, password of tabellen. Begin direct met implementeren.

## Credentials (.env)

```
DB_API_URL={api_url}
DB_USERNAME={database.username}
DB_PASSWORD={password}
```

## Server / IP

- **API URL (gebruik dit):** {api_url}
- **Admin panel:** {admin_panel}
- **IP/host:** {host_ip}
- Poort: {server_port} (alles op één poort)
- Lokaal op dezelfde PC: `http://localhost:{server_port}/api/{database.username}/<password>/` werkt ook
- Root `http://{host_ip}:{server_port}/` geeft bewust `ERROR not found` (veiligheid)

## Database info

- Naam: {database.name}
- Slug: {database.slug}
- ID: {database.id}
- API URL: {api_url}
- Username: {database.username}
- Password: {password}

## Authenticatie

Credentials zitten **in het URL-pad** — geen aparte login of Bearer token nodig:

```
{api_url}/<endpoint>
```

Voorbeeld: `GET {api_url}/products`

## Endpoints

| Method | Endpoint | Beschrijving |
|--------|----------|--------------|
| GET | / | Database info |
| GET | /tables | Schema overzicht |
| GET | /{{table}} | Lijst rijen (?limit=50&offset=0&sort=kolom) |
| GET | /{{table}}/{{id}} | Enkele rij |
| POST | /{{table}} | Insert (JSON body) |
| PATCH | /{{table}}/{{id}} | Update |
| DELETE | /{{table}}/{{id}} | Verwijder |

## Automatische kolommen (schema-less API)

Bij **POST** en **PATCH** worden onbekende kolommen in de JSON body **automatisch aangemaakt**:
- Metadata (admin schema) wordt bijgewerkt
- SQLite krijgt `ALTER TABLE ADD COLUMN`
- Type wordt afgeleid van de waarde: string→text, number→integer/float, bool→boolean, object/array→json

Voorbeeld — tabel `products` heeft alleen `id` en `name`, je stuurt:
```json
{{ "name": "Apple", "price": 1.50, "in_stock": true }}
```
→ kolommen `price` (float) en `in_stock` (boolean) worden automatisch toegevoegd.

Je hoeft kolommen **niet** vooraf in admin aan te maken — stuur ze mee in je API requests.

## Tabellen in deze database

{tables_summary}

Tabellen: {table_names_str}

{table_commands}

## Wat je moet doen

1. Maak een herbruikbare API-client module/service in mijn project
2. Zet bovenstaande `.env` variabelen in mijn project (`.env` / `.env.local`)
3. Implementeer een fetch wrapper die `DB_API_URL` als base gebruikt (credentials al in URL)
4. Implementeer CRUD helpers voor elke tabel hierboven
5. Vervang mock/hardcoded data door echte API calls naar `{api_url}`
6. Gebruik automatische kolommen: stuur nieuwe velden mee in POST/PATCH — ze worden zelf aangemaakt
7. Foutafhandeling: 401 → ongeldige credentials, 404 → niet gevonden, 422 → validatiefout
8. Begin direct — vraag geen extra database informatie

## Voorbeeld client (JavaScript — kopieer en pas aan)

```javascript
{js_client}
```

## Kolomtypes

text, integer, float, boolean, datetime, json — integer primary keys krijgen auto-increment bij POST.

Nieuwe kolommen via API worden automatisch getyped op basis van de meegestuurde waarde.
"""
