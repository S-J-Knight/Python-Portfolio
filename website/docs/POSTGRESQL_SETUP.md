# PostgreSQL Setup Guide for Knightcycle

## Step 1: Install PostgreSQL

### Option A: Using Installer (Recommended for Windows)
1. Download PostgreSQL from: https://www.postgresql.org/download/windows/
2. Run the installer (version 16.x recommended)
3. During installation:
   - Remember the password you set for the `postgres` user
   - Default port: 5432 (keep this)
   - Locale: Default locale
   - Install pgAdmin 4 (GUI tool - helpful)

### Option B: Using Winget
```powershell
winget install PostgreSQL.PostgreSQL
```

## Step 2: Verify Installation
```powershell
# Check if PostgreSQL service is running
Get-Service -Name postgresql*

# If not running, start it:
Start-Service postgresql-x64-16  # Or your version number
```

## Step 3: Create Database and User

Open PowerShell as Administrator and run:

```powershell
# Connect to PostgreSQL as postgres user
# Default password is what you set during installation
psql -U postgres

# In the PostgreSQL prompt (postgres=#), run these commands:
CREATE DATABASE knightcycle_db;
CREATE USER knightcycle_user WITH PASSWORD 'your_secure_password_here';
ALTER ROLE knightcycle_user SET client_encoding TO 'utf8';
ALTER ROLE knightcycle_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE knightcycle_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE knightcycle_db TO knightcycle_user;

# Grant schema permissions (PostgreSQL 15+)
\c knightcycle_db
GRANT ALL ON SCHEMA public TO knightcycle_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO knightcycle_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO knightcycle_user;

# Exit PostgreSQL prompt
\q
```

## Step 4: Install Python PostgreSQL Adapter

```powershell
cd c:\Users\havea\Desktop\Portfolio\Python-Portfolio\website
pip install psycopg2-binary
```

## Step 5: Environment Variables

Create `.env` file in the `website` directory (if not exists):

```env
# Database Configuration
DB_NAME=knightcycle_db
DB_USER=knightcycle_user
DB_PASSWORD=your_secure_password_here
DB_HOST=localhost
DB_PORT=5432

# Django Secret Key (generate a new one for production)
SECRET_KEY=your-secret-key-here

# Debug Mode
DEBUG=True
```

**IMPORTANT:** Add `.env` to `.gitignore` to never commit passwords!

## Step 6: Backup SQLite Data

```powershell
# Export data from SQLite
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 4 > data_backup.json
```

## Step 7: Apply Migrations to PostgreSQL

Settings are already updated to use PostgreSQL. Now run:

```powershell
# Run migrations
python manage.py migrate

# Load the backed up data
python manage.py loaddata data_backup.json

# Create superuser (if needed)
python manage.py createsuperuser
```

## Step 8: Test the Migration

```powershell
# Start development server
python manage.py runserver

# Visit:
# - http://127.0.0.1:8000/admin
# - Check products, orders, customers
# - Test placing an order
# - Verify WTN generation
```

## Troubleshooting

### Error: "Peer authentication failed"
Edit `pg_hba.conf` (usually in `C:\Program Files\PostgreSQL\16\data\`):
Change:
```
host    all             all             127.0.0.1/32            scram-sha-256
```

### Error: "Password authentication failed"
- Verify password in `.env` matches what you set
- Reset password if needed:
```sql
ALTER USER knightcycle_user WITH PASSWORD 'new_password';
```

### Error: "Permission denied for schema public"
Run the GRANT commands from Step 3 again.

### Can't connect to PostgreSQL
```powershell
# Check if PostgreSQL is running
Get-Service postgresql*

# Start if needed
Start-Service postgresql-x64-16
```

## Rolling Back (if needed)

If something goes wrong, you can revert to SQLite:

1. Comment out the PostgreSQL DATABASES config in `settings.py`
2. Uncomment the SQLite DATABASES config
3. Your `db.sqlite3` file still has all the data

## Production Deployment Notes

For production (IONOS or other hosting):

1. **Never use SQLite in production**
2. Use managed PostgreSQL service if available
3. Set `DEBUG=False` in production `.env`
4. Use strong, unique passwords
5. Enable SSL for database connections
6. Regular automated backups
7. Monitor database performance

## Useful Commands

```powershell
# Connect to database
psql -U knightcycle_user -d knightcycle_db

# List databases
\l

# List tables
\dt

# Describe table
\d store_product

# Exit
\q

# Backup database
pg_dump -U knightcycle_user knightcycle_db > backup.sql

# Restore database
psql -U knightcycle_user knightcycle_db < backup.sql
```

## Next Steps After Migration

1. ✅ Update `docs/to_do.txt` - mark database migration complete
2. ✅ Set up automated backups
3. ✅ Test all features thoroughly
4. ✅ Update deployment documentation
5. ✅ Configure backup strategy

## Benefits You Now Have

- ✅ Production-ready database
- ✅ Better concurrency handling
- ✅ Faster queries with proper indexing
- ✅ Full ACID compliance
- ✅ Ready for scaling
- ✅ Industry standard for Django
