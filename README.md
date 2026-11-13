# osu! Malaysia Top 15 Voting Platform

A full-stack, production-ready community voting platform for the osu! Malaysia Top 15. Built with Django, MariaDB, and deployed via Cloudflare Tunnel + Nginx.

## Features

### User Features
- **osu! OAuth Integration:** Seamless login using official osu! credentials.
- **Eligibility Gate:** Blocks accounts created on or after January 1, 2026.
- **Interactive Voting:** Drag-and-drop UI (SortableJS) to rank exactly 15 Malaysian players.
- **Auto-Save Drafts:** Uses `localStorage` to save votes and comments locally, preventing data loss if the page is closed.
- **Private Comments:** Add up to 500 characters per player.
- **Public Share Links:** Generate a read-only, public URL of your Top 15 to share on Discord/Twitter. Links can be rotated or revoked.
- **Dark/Light Mode:** Persistent theme toggle.

### Admin & Backend Features
- **Automated Player Pool:** A management command fetches the top Malaysian players (>8000pp) from the osu! API and updates ranks/PP.
- **Flagging System:** Automatically flags suspicious ballots (inactive players, rapid submits, low PP picks).
- **Review Queue & Veto:** Admins can inspect flagged ballots, void them, un-void them, or permanently ban voters.
- **Audit Trail:** Immutable logging of ballot creation, edits, and void actions.
- **Export Engine:** Generates a `.zip` file containing a formatted Excel workbook (Summary, Final Rankings, Trimmed Rankings, Ballots Wide/Long, Comments) and per-player `.txt` comment files for video editors.
- **Security:** CSRF protection, rate limiting (votes and comments), and strict production headers.

## Tech Stack
- **Backend:** Python 3.13, Django 5.2
- **Database:** MariaDB (MySQL compatible)
- **Frontend:** HTML5, Vanilla CSS, Vanilla JS, SortableJS
- **Deployment:** Debian 13, Gunicorn, Nginx, Cloudflare Tunnel (Zero Trust)

## Local Development Setup
1. Clone the repo and create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
2. Install dependencies:

    ```bash
    pip install -r requirements.txt
3. Copy `.env.example` to .env and fill in your osu! API credentials, MySQL database details, and generate a `DJANGO_SECRET_KEY`.

4. Run migrations and collect static files:

    ```bash
    python manage.py migrate
    python manage.py collectstatic --noinput
5. Create a superuser and run the server:

    ```bash
    python manage.py createsuperuser
    python manage.py runserver
## Production Deployment (Debian + Cloudflare)
This project is configured to run behind Cloudflare Tunnel to bypass NAT/Proxmox firewall restrictions.

- **Gunicorn**: Managed via `systemd` (`/etc/systemd/system/gunicorn.service`).

- **Nginx**: Acts as a reverse proxy (`/etc/nginx/conf.d/<site_name>.site.conf`).

- **Cloudflare**: Handles SSL termination and DNS routing via `cloudflared`.

To update the live site after making changes:

    
    python manage.py collectstatic --noinput
    sudo systemctl restart gunicorn
    # Purge cache in Cloudflare Dashboard
## Upcoming Features (v2.0)
□ YouTube clip embedding for players.

□ Player bios (self-described).

□ Hexagon radar charts for tournament skill points (Skill Issue bot integration).
