-- Restaurants discovered via search; place_id links to Google Places later.
create table restaurants (
  id          uuid primary key default gen_random_uuid(),
  place_id    text unique,
  name        text not null,
  address     text,
  lat         numeric,
  lng         numeric,
  created_at  timestamptz not null default now()
);

-- Menu items with AI-estimated nutrition inline.
-- estimated_at is null until Gemini has processed the item.
create table menu_items (
  id             uuid primary key default gen_random_uuid(),
  restaurant_id  uuid not null references restaurants (id) on delete cascade,
  name           text not null,
  description    text,
  price_cents    int,
  calories       int,
  protein_g      numeric,
  carbs_g        numeric,
  fat_g          numeric,
  dietary_tags   text[],
  estimated_at   timestamptz,
  created_at     timestamptz not null default now(),
  unique (restaurant_id, name)
);

create index menu_items_restaurant_id_idx on menu_items (restaurant_id);

-- RLS: anyone can read the cached data (it's public menu info);
-- writes only happen from Edge Functions using the service role key,
-- which bypasses RLS — so no insert/update policies for clients.
alter table restaurants enable row level security;
alter table menu_items enable row level security;

create policy "public read restaurants"
  on restaurants for select
  using (true);

create policy "public read menu_items"
  on menu_items for select
  using (true);
