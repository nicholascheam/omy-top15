# CONTRACT — osu! Top 15 Malaysia Voting Site

This file is never edited after this commit.
Any change to an earlier decision is implemented as a NEW migration,
NEW URL, NEW template, or NEW view — never as an edit to this file.

---

## A1 — Data model fields

Django models live in `core/models.py`. Field types below are final.

### A1.1 OsuUser
| Field | Type | Notes |
|---|---|---|
| id | BigAutoField | PK |
| osu_user_id | BigIntegerField | unique, indexed |
| username | CharField(64) | |
| avatar_url | URLField(255) | |
| country_code | CharField(2) | |
| join_date | DateTimeField | from osu! `/me` |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |

### A1.2 VotingCycle
| Field | Type | Notes |
|---|---|---|
| id | BigAutoField | PK |
| name | CharField(64) | unique |
| start_time | DateTimeField | |
| end_time | DateTimeField | deadline |
| status | CharField(16) | choices: draft / active / closed |
| created_at | DateTimeField | auto_now_add |

### A1.3 Player
| Field | Type | Notes |
|---|---|---|
| id | BigAutoField | PK |
| osu_user_id | BigIntegerField | unique, indexed |
| username | CharField(64) | |
| avatar_url | URLField(255) | |
| country_code | CharField(2) | default "MY" |
| current_pp | IntegerField | refreshed from osu! |
| is_active | BooleanField | default True (eligibility) |
| last_refreshed_at | DateTimeField | auto_now |
| created_at | DateTimeField | auto_now_add |

### A1.4 Ballot
| Field | Type | Notes |
|---|---|---|
| id | BigAutoField | PK |
| user | FK → OsuUser | on_delete CASCADE |
| cycle | FK → VotingCycle | on_delete CASCADE |
| submitted_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |
| flag_reason | TextField | blank, default "" |
| is_voided | BooleanField | default False |
| void_reason | TextField | blank, default "" |
| voided_by | FK → OsuUser | null, blank, related_name "+" |
| voided_at | DateTimeField | null, blank |

Constraint: UniqueConstraint(fields=["user", "cycle"], name="unique_ballot_per_user_cycle")

### A1.5 BallotEntry
| Field | Type | Notes |
|---|---|---|
| id | BigAutoField | PK |
| ballot | FK → Ballot | on_delete CASCADE, related_name "entries" |
| player | FK → Player | on_delete PROTECT |
| rank_position | PositiveSmallIntegerField | 1..15 |
| points | PositiveSmallIntegerField | 1..15 |

Constraints:
- UniqueConstraint(ballot, rank_position, name="unique_rank_per_ballot")
- UniqueConstraint(ballot, player, name="unique_player_per_ballot")
- CheckConstraint(rank_position >= 1 AND rank_position <= 15, name="rank_between_1_and_15")
- CheckConstraint(points >= 1 AND points <= 15, name="points_between_1_and_15")

### A1.6 Comment
| Field | Type | Notes |
|---|---|---|
| id | BigAutoField | PK |
| user | FK → OsuUser | on_delete CASCADE |
| player | FK → Player | on_delete CASCADE |
| body | TextField | max_length 500 (enforced on model + form) |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |

Constraint: UniqueConstraint(user, player, name="unique_comment_per_user_player")
Note: comments are NOT cycle-scoped; cycle filtering happens at export.

### A1.7 ShareLink
| Field | Type | Notes |
|---|---|---|
| id | BigAutoField | PK |
| ballot | OneToOneField → Ballot | on_delete CASCADE |
| token | CharField(64) | unique, indexed |
| revoked | BooleanField | default False |
| created_at | DateTimeField | auto_now_add |

### A1.8 BallotAudit
| Field | Type | Notes |
|---|---|---|
| id | BigAutoField | PK |
| ballot | FK → Ballot | on_delete CASCADE |
| action | CharField(16) | choices: create / edit / void / unvoid |
| actor | FK → OsuUser | null (system actions) |
| snapshot | JSONField | pre/post entry lists |
| created_at | DateTimeField | auto_now_add |

Immutable: no edit or delete paths are ever written for this model.

### A1.9 BannedUser — RESERVED, added by a new migration in Step 72
| Field | Type | Notes |
|---|---|---|
| id | BigAutoField | PK |
| osu_user_id | BigIntegerField | unique |
| banned_by | FK → OsuUser | null |
| banned_at | DateTimeField | auto_now_add |
| reason | TextField | blank |

---

## A2 — URL routes

| Path | Method | View | Auth |
|---|---|---|---|
| / | GET | home | public |
| /login | GET | login_redirect | public |
| /oauth/callback | GET | oauth_callback | public |
| /logout | POST | logout_view | login |
| /vote | GET/POST | vote | login + pre-2026 |
| /my-ballot | GET | my_ballot | login |
| /my-ballot/edit | GET/POST | edit_ballot | login |
| /my-ballot/comment | POST | submit_comment | login |
| /my-ballot/comment/<id>/edit | POST | edit_comment | login (owner) |
| /my-ballot/comment/<id>/delete | POST | delete_comment | login (owner) |
| /my-ballot/share | POST | create_share | login (owner) |
| /my-ballot/share/revoke | POST | revoke_share | login (owner) |
| /s/<token> | GET | public_share | public |
| /api/players/search | GET | search_players | login |
| /admin/ | — | Django admin | admin |
| /admin/review | GET | review_list | admin |
| /admin/review/<ballot_id> | GET | review_detail | admin |
| /admin/review/<ballot_id>/void | POST | review_void | admin |
| /admin/review/<ballot_id>/unvoid | POST | review_unvoid | admin |
| /admin/review/<ballot_id>/dismiss | POST | review_dismiss | admin |
| /admin/export | POST | export_results | admin |

---

## A3 — Environment variables (loaded via django-environ)

DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS,
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT,
OSU_CLIENT_ID, OSU_CLIENT_SECRET, OSU_REDIRECT_URI,
ADMIN_OSU_IDS, SITE_BASE_URL

---

## A4 — Packages (pinned, no others)
Django==5.0.*
mysqlclient
requests
django-environ
openpyxl
gunicorn

Dev-only, not in requirements.txt: `pip-audit` (Step 90).
Client-side CDN, not a Python package: SortableJS (Step 50).

---

## A5 — Template filenames

base.html, home.html, login.html, vote.html, my_ballot.html,
ballot_confirmation.html, share_public.html,
admin_review_list.html, admin_review_detail.html

---

## A6 — External APIs

- POST https://osu.ppy.sh/oauth/token
- GET  https://osu.ppy.sh/api/v2/me
- GET  https://osu.ppy.sh/api/v2/rankings/osu/performance

Authorize URL (client-side redirect): https://osu.ppy.sh/oauth/authorize

---

## A7 — Constants (restated from v3, referenced by later steps)

| Name | Value |
|---|---|
| BALLOT_SIZE | 15 entries, ranks 1–15, points 1–15 |
| COMMENT_MAX_LEN | 500 |
| VOTER_MIN_JOIN_DATE | 2026-01-01 (accounts created on/after this cannot vote) |
| PP_THRESHOLD_AT_CLOSE | 8880 |
| PP_OUTLIER_FLAG | < 7000 |
| NEW_ACCOUNT_FLAG_DAYS | 30 |
| SHARE_TOKEN_BYTES | 32 (secrets.token_urlsafe) |
| VOTE_RATE_LIMIT | 10 / hour / user |
| COMMENT_RATE_LIMIT | 10 / hour / user |
| SEARCH_MIN_CHARS | 2 |
| SEARCH_RESULT_LIMIT | 20 |
| RANKINGS_PER_PAGE | 50 |