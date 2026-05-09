# Supabase Security Advisor Notes

Last reviewed: 2026-05-09

## `public.spatial_ref_sys` RLS warning

Supabase may show `RLS Disabled in Public` for `public.spatial_ref_sys`.

This table is created by the PostGIS extension and stores coordinate system metadata, not Fullet user, station, price, admin, or token data. The warning is related to Supabase's general rule that all public-schema tables exposed to the Data API should have RLS enabled.

On this project, trying to enable RLS from SQL Editor can fail with:

```text
ERROR: 42501: must be owner of table spatial_ref_sys
```

That means the table is owned by the PostGIS extension owner. Do not run `DROP EXTENSION postgis CASCADE` on the live app to fix this warning; PostGIS backs the station location column and nearby-station RPCs.

Safe diagnostic:

```text
database/postgis_spatial_ref_sys_owner_check.sql
```

Best long-term fix:

- Create a database backup first.
- Move/reinstall PostGIS in a non-public schema such as `extensions`/`gis`, following Supabase's PostGIS troubleshooting guidance.
- Because PostGIS 2.3+ is not normally relocatable, Supabase documents either a backup/drop/recreate/restore flow or contacting Supabase Support to perform the relocation.

Release decision:

- This advisory does not block Fullet's Google Play internal testing.
- It should remain as an accepted infrastructure advisory until a planned database maintenance window.
