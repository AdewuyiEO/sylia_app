-- Aura — Postgres schema (Supabase). Run in the SQL editor.
-- Every table is row-level-security scoped to the authenticated user.

-- ---------- profiles ----------
create table profiles (
  id            uuid primary key references auth.users on delete cascade,
  taste         jsonb   not null default '{}',   -- palette + axes
  fit_profile   jsonb   not null default '{}',   -- per-category fit, sizes
  streak        int     not null default 0,
  last_wear     date,
  is_pro        boolean not null default false,
  created_at    timestamptz not null default now()
);

-- ---------- garments ----------
create table garments (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users on delete cascade,
  type          text not null,          -- GarmentTypeId
  color         text not null,          -- ColorId (dominant)
  colors        text[] not null default '{}',
  material      text not null,
  warmth        int  not null,          -- 0..4
  formality     int  not null,          -- 1..5
  status        text not null default 'active',  -- active|laundry|archived|processing
  tags          jsonb not null default '[]',     -- [{value,source,confidence}]
  confirmed     boolean not null default false,
  image_url     text,
  cutout_url    text,
  brand         text,
  size          text,
  price         numeric,
  wear_count    int not null default 0,
  last_worn_at  timestamptz,
  created_at    timestamptz not null default now()
);
create index on garments (user_id, status);

-- ---------- outfits ----------
create table outfits (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users on delete cascade,
  garment_ids   uuid[] not null,
  composite_url text,
  reason        text not null,          -- <=96 chars, always present
  source        text not null,          -- drop|generated|manual|mirror
  context       jsonb not null default '{}',
  wear_count    int not null default 0,
  last_worn_at  timestamptz,
  saved_at      timestamptz,
  created_at    timestamptz not null default now()
);
create index on outfits (user_id);

-- ---------- wear_events (ground-truth signal) ----------
create table wear_events (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users on delete cascade,
  outfit_id     uuid references outfits on delete set null,
  garment_ids   uuid[] not null,
  photo_url     text,
  worn_at       timestamptz not null default now()
);
create index on wear_events (user_id, worn_at desc);

-- ---------- style_signals (feeds personalization) ----------
create table style_signals (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users on delete cascade,
  type          text not null,          -- wear|save|pass|reason|dwell
  target_type   text not null,          -- outfit|garment|attribute
  target_id     text,
  weight        numeric not null,
  reason        text,
  created_at    timestamptz not null default now()
);

-- ---------- style_beliefs (human-readable Style Memory) ----------
create table style_beliefs (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users on delete cascade,
  statement     text not null,          -- "You wear trainers to work"
  evidence      jsonb not null default '{}',
  confidence    numeric not null default 0.5,
  muted         boolean not null default false,
  created_at    timestamptz not null default now()
);

-- ---------- RLS ----------
alter table profiles       enable row level security;
alter table garments       enable row level security;
alter table outfits        enable row level security;
alter table wear_events    enable row level security;
alter table style_signals  enable row level security;
alter table style_beliefs  enable row level security;

create policy "own profile"  on profiles      for all using (auth.uid() = id)      with check (auth.uid() = id);
create policy "own garments" on garments      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own outfits"  on outfits       for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own wears"    on wear_events   for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own signals"  on style_signals for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own beliefs"  on style_beliefs for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ---------- storage buckets (create in dashboard, then policy) ----------
-- garments/  composites/  wears/  — all private; access via signed URLs.
