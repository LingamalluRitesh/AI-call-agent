create extension if not exists pgcrypto;

create table if not exists public.call_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  provider_call_id text unique,
  caller_name text,
  caller_number text,
  detected_language text,
  call_reason text,
  urgency text not null default 'normal'
    check (urgency in ('low','normal','high','emergency')),
  summary text,
  callback_required boolean not null default true,
  preferred_callback_time text,
  status text not null default 'received',
  recording_status text not null default 'not_started'
    check (recording_status in ('not_started','awaiting_consent','recording','declined','not_recorded','failed','deleted')),
  recording_storage_path text,
  recording_retention_until timestamptz,
  started_at timestamptz,
  ended_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.call_transcripts (
  id uuid primary key default gen_random_uuid(),
  call_id uuid not null references public.call_logs(id) on delete cascade,
  speaker text not null check (speaker in ('assistant','caller','system')),
  content text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.call_recording_consents (
  id uuid primary key default gen_random_uuid(),
  call_id uuid not null references public.call_logs(id) on delete cascade,
  consent text not null check (consent in ('yes','no','unknown')),
  disclosure_text text not null,
  disclosure_language text,
  captured_at timestamptz not null default now()
);

create table if not exists public.voice_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  provider text not null,
  provider_voice_id text not null,
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  unique(user_id, provider)
);

alter table public.call_logs enable row level security;
alter table public.call_transcripts enable row level security;
alter table public.call_recording_consents enable row level security;
alter table public.voice_profiles enable row level security;

create policy "Users read own calls" on public.call_logs
  for select using (auth.uid() = user_id);
create policy "Users read own transcripts" on public.call_transcripts
  for select using (
    exists (select 1 from public.call_logs c
            where c.id = call_id and c.user_id = auth.uid())
  );
create policy "Users read own recording consents" on public.call_recording_consents
  for select using (
    exists (select 1 from public.call_logs c
            where c.id = call_id and c.user_id = auth.uid())
  );
create policy "Users manage own voice profile" on public.voice_profiles
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Create a PRIVATE Supabase Storage bucket named call-recordings in the dashboard.
-- Do not enable public access. Add owner-scoped storage policies before production.
-- Backend writes must use a protected server-side role; never expose service role to Android.
