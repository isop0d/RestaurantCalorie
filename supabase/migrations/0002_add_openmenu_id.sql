-- OpenMenu restaurant ID — the upsert key for menu data fetched from OpenMenu.
-- (place_id remains reserved for Google Places integration.)
alter table restaurants add column openmenu_id text unique;
