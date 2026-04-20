-- Charge / wallet / ledger migration for Supabase Postgres
-- The application still keeps `users.balance` as the legacy source of truth,
-- so this migration mirrors that value into `wallets.available_balance`.

create table if not exists wallets (
  user_id text primary key references users(id) on delete cascade,
  available_balance bigint not null default 0,
  pending_balance bigint not null default 0,
  created_at text not null default now()::text,
  updated_at text not null default now()::text
);

create table if not exists charge_orders (
  id text primary key,
  order_code text not null unique,
  user_id text not null references users(id) on delete cascade,
  amount bigint not null check (amount > 0),
  vat_amount bigint not null default 0,
  total_amount bigint not null check (total_amount >= amount),
  payment_channel text not null,
  payment_method_detail text not null default '',
  status text not null default 'created',
  depositor_name text not null default '',
  receipt_type text not null default 'none',
  receipt_payload_json jsonb not null default '{}'::jsonb,
  reference text not null default '',
  pg_provider text not null default '',
  pg_order_id text not null default '',
  pg_payment_key text not null default '',
  failure_reason text not null default '',
  expires_at text not null default '',
  paid_at text not null default '',
  created_at text not null default now()::text,
  updated_at text not null default now()::text
);

create index if not exists idx_charge_orders_user_created_at
  on charge_orders(user_id, created_at desc);

create table if not exists wallet_ledger (
  id text primary key,
  user_id text not null references users(id) on delete cascade,
  entry_type text not null,
  amount bigint not null,
  balance_after bigint not null,
  related_charge_order_id text references charge_orders(id) on delete set null,
  related_order_id text references orders(id) on delete set null,
  memo text not null default '',
  created_at text not null default now()::text
);

create index if not exists idx_wallet_ledger_user_created_at
  on wallet_ledger(user_id, created_at desc);

insert into wallets (user_id, available_balance, pending_balance, created_at, updated_at)
select id, balance, 0, now()::text, now()::text
from users
on conflict (user_id) do update
set available_balance = excluded.available_balance,
    updated_at = excluded.updated_at;

insert into wallet_ledger (
  id,
  user_id,
  entry_type,
  amount,
  balance_after,
  related_charge_order_id,
  related_order_id,
  memo,
  created_at
)
select
  'legacy_' || bt.id,
  bt.user_id,
  case
    when bt.kind = 'charge' then 'charge'
    when bt.kind = 'order' then 'order_debit'
    when bt.kind = 'admin_adjust' then 'admin_adjustment'
    else 'admin_adjustment'
  end,
  bt.amount,
  bt.balance_after,
  null,
  null,
  bt.memo,
  bt.created_at
from balance_transactions bt
on conflict (id) do nothing;
