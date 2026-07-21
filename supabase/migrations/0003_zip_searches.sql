-- Cache of a zip code's restaurant search results (one row per zip + country).
-- Stores the FULL restaurant list OpenMenu returned, so repeat searches — and
-- "show more restaurants" (returning more of the same list) — are a single DB
-- read. Menus are NOT stored here; they live in menu_items and load lazily when
-- a restaurant is opened.
create table zip_searches (
  zip          text not null,
  country      text not null default 'US',
  restaurants  jsonb not null,
  created_at   timestamptz not null default now(),
  primary key (zip, country)
);

alter table zip_searches enable row level security;

create policy "public read zip_searches"
  on zip_searches for select
  using (true);
