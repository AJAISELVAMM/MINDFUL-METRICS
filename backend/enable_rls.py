import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

with engine.begin() as conn:
    # 1. Fetch all tables in schema 'public'
    tables = conn.execute(text("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """)).scalars().all()
    
    print(f"Found {len(tables)} tables in schema 'public'. Enabling RLS...")
    
    for table in tables:
        conn.execute(text(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;'))
        print(f"  [ENABLED RLS] {table}")

print("\nVerifying RLS status for all public tables...")
with engine.connect() as conn:
    results = conn.execute(text("""
        SELECT tablename, rowsecurity
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """)).fetchall()
    
    all_enabled = True
    for r in results:
        status = "ENABLED" if r[1] else "DISABLED"
        print(f"  {r[0]}: RLS {status}")
        if not r[1]:
            all_enabled = False

    # Check the standard Supabase Security Advisor linter query for 'rls_disabled_in_public'
    unsecured = conn.execute(text("""
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'p')
          AND c.relrowsecurity = false;
    """)).scalars().all()
    
    if not unsecured:
        print("\n[SUCCESS] Supabase Security Advisor check passed: 0 public tables with RLS disabled!")
    else:
        print(f"\n[WARNING] Tables still with RLS disabled: {unsecured}")
