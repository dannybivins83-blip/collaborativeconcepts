# SiteCam ↔ WWS — Integration (shared source of truth)

One doc both sides work from:
- **WWS** = this repo (`collaborativeconcepts`) — public OSHA Walking-Working Surfaces site + CRM. Flask `api/index.py` on Vercel, Upstash KV.
- **SiteCam** = `sitecam` repo — multi-tenant field-photo platform. NestJS + Postgres + Redis + S3 at `https://sitecam-api.onrender.com`.

## Model
Key-per-tenant: the `x-api-key` **is** the tenant (no caller-supplied tenant param). WWS consumes SiteCam's read-only `/api/ext/*`. The `wws` tenant is isolated and currently empty — a WWS key only ever reaches WWS data; a cross-tenant/unknown id returns **404**.

## Contract — SiteCam `/api/ext/*` (auth: `x-api-key`)
| Method | Path | Returns | Status |
|---|---|---|---|
| GET | `/api/ext/projects?q=<address\|name>` | `[{id,name,address,system,status,crmJobId,photoCount}]` | ✅ live |
| GET | `/api/ext/projects/:id/photos` | `{project:{id,name,address,system}, photos:[{url,thumbUrl,capturedAt,gps,description}]}` | ✅ live |
| POST | `/api/ext/projects` | body `{name,address,crmJobId}` → `{id,name,address,crmJobId,system}`, **idempotent on `crmJobId`** | ✅ live |
| GET | `/api/ext/projects?crmJobId=<id>` | exact match (deterministic) | ✅ live |

Photos are **public/durable Cloudflare R2** objects (no signing, no expiry) — embeddable straight into the PDF.

## Env vars
| Side | Variable | Value |
|---|---|---|
| SiteCam (Render `sitecam-api`) | `SITECAM_API_KEY_WWS` | shared secret *(set separately — never commit the value)* |
| WWS (Vercel) | `SITECAM_API_KEY` | **same** value as above |
| WWS (Vercel) | `SITECAM_BASE_URL` | `https://sitecam-api.onrender.com` |

## WWS consumer — already built & deployed (`api/index.py`, config-gated by both env vars)
- `GET /api/admin/sitecam/status` → `{configured, base}`
- `POST /api/admin/inspection/<id>/sitecam/start` → one-click **create** (idempotent on `crmJobId=wws-<id>`) the SiteCam project for this inspection
- `GET /api/admin/inspection/<id>/sitecam/search?q=` → search SiteCam projects (defaults q to the inspection's property address)
- `POST /api/admin/inspection/<id>/sitecam/link` `{projectId}` → store the chosen project on the inspection
- `POST /api/admin/inspection/<id>/sitecam/pull` → pull that project's photos into `inspection.photos`

Auth header sent: `x-api-key`. Everything is gated by `_sitecam_on()` (both env vars present) — **inert and safe until the key is set**.

---

# 3-Step Plan

## Step 1 — Turn on the read path *(handshake — unblocks immediately)*
- **SiteCam (Render):** set `SITECAM_API_KEY_WWS = <shared value>` → save/redeploy.
- **WWS (Vercel):** `SITECAM_API_KEY = <same value>` + `SITECAM_BASE_URL = https://sitecam-api.onrender.com` → redeploy.
- **Verify:** `GET /api/ext/projects?q=test` w/ WWS key → `200 []`; a SeaBreeze project id on `/photos` w/ WWS key → `404`; WWS `/api/admin/sitecam/status` → `configured:true`.
- ✅ **Done when:** WWS shows `configured:true` and search returns an empty list.

## Step 2 — Write path + field capture *(populate the `wws` tenant)*
- **SiteCam builds** (scoped to the key's tenant): `POST /api/ext/projects {name,address,crmJobId}` (idempotent on `crmJobId`); deterministic lookup by `crmJobId`; **WWS field-crew logins** in the `wws` tenant with photo-capture access.
- **WWS builds:** "Start field capture" on an inspection → `POST /api/ext/projects {crmJobId:"wws-<inspId>", name, address}`, store the returned `id`, hand the crew a deep link to shoot in SiteCam.
- ✅ **Done when:** "Start field capture" creates/finds the SiteCam project and a crew member can add photos to it.

## Step 3 — Photos into the deliverables *(close the loop)*
- **SiteCam:** confirm whether `url`/`thumbUrl` are **public-durable** or **signed/expiring**.
- **WWS builds:** "Pull photos" → `GET /api/ext/projects/:id/photos` → embed thumbnails in the **inspection-report PDF** photo log + show in the **client portal** document center. (If URLs expire, WWS fetches + caches at generate time.)
- ✅ **Done when:** a generated WWS inspection report shows the field photos and the client sees them in their portal.

---

## Status checklist
- [x] WWS consumer aligned to `/api/ext/*` (x-api-key, search→link→pull, new photo shape) — built & deployed
- [x] SiteCam `/api/ext/*` + per-tenant isolation + 404 on cross-tenant id
- [x] `wws` tenant created (isolated, empty)
- [x] `SITECAM_BASE_URL` set on Vercel
- [ ] **Step 1:** shared key set on both dashboards *(pending — your courier)*
- [ ] **Step 2:** SiteCam `POST /api/ext/projects` + `crmJobId` lookup ✅ · WWS one-click "Start field capture" ✅ · **WWS crew logins in the `wws` tenant ⬜ (pending — names/emails or generic logins)**
- [ ] **Step 3:** photos are public/durable R2 ✅ · WWS embeds thumbnails in the report PDF ✅ · client-portal document center ⬜

## Open question
- Photo `url`/`thumbUrl`: public-durable or signed/expiring? (decides Step 3 rendering)
