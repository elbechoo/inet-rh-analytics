"""Recording the audit trail.

One entry point, `record()`, used by every action worth remembering.

Two rules shape the design:

* **Auditing must never break the thing it audits.** If writing the trail fails,
  the leave approval it was recording still has to succeed. Every failure here
  is swallowed and logged, never raised.

* **The trail is written in its own transaction.** If it shared the caller's
  session, a later rollback would erase the record of an action that partly
  happened - exactly the case you most want a record of.
"""
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)

# Actions worth a permanent record: anything that changes pay, employment
# status, access, or a decision an employee could later dispute.
LEAVE_APPROVE   = "conge.valider"
LEAVE_REJECT    = "conge.refuser"
LEAVE_CANCEL    = "conge.annuler"
EMPLOYEE_CREATE = "employe.creer"
EMPLOYEE_UPDATE = "employe.modifier"
EMPLOYEE_DELETE = "employe.supprimer"
ROLE_CHANGE     = "utilisateur.role"
STATUS_CHANGE   = "utilisateur.statut"
PASSWORD_RESET  = "utilisateur.reset_password"
DOC_VALIDATE    = "document.valider"
HOLIDAY_CHANGE  = "jour_ferie.modifier"
DATA_IMPORT     = "import.commit"


def _short(value, limit: int = 500) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    s = str(value)
    return s if len(s) <= limit else s[: limit - 1] + "..."


def record(
    action: str,
    actor: dict | None = None,
    entite: str | None = None,
    entite_id: int | None = None,
    cible_employe_id: int | None = None,
    ancienne_valeur=None,
    nouvelle_valeur=None,
    detail: str | None = None,
    request=None,
) -> None:
    """Write one audit entry. Never raises.

    `actor` is the dict returned by get_current_user. `request` is optional and
    only used to capture the client IP.
    """
    try:
        from config.database import session_factory_for
        from models.models import AuditLog, Utilisateur
        from config import tenants

        # Same workspace as the request that triggered it, so one client's trail
        # never lands in another's database.
        tenant = tenants.resolve_tenant(request) if request is not None else tenants.DEFAULT_TENANT
        try:
            factory = session_factory_for(tenant)
        except KeyError:
            factory = session_factory_for(tenants.DEFAULT_TENANT)

        ip = None
        if request is not None:
            client = getattr(request, "client", None)
            ip = getattr(client, "host", None)
            # Behind Caddy the real address is in the forwarded header.
            fwd = request.headers.get("x-forwarded-for") if hasattr(request, "headers") else None
            if fwd:
                ip = fwd.split(",")[0].strip()

        user_id = (actor or {}).get("user_id")
        role = (actor or {}).get("role")

        db = factory()
        try:
            username = None
            if user_id:
                u = db.query(Utilisateur).filter(Utilisateur.user_id == user_id).first()
                username = u.username if u else None

            db.add(AuditLog(
                user_id=user_id,
                username=username,
                role=role,
                action=action,
                entite=entite,
                entite_id=entite_id,
                cible_employe_id=cible_employe_id,
                ancienne_valeur=_short(ancienne_valeur),
                nouvelle_valeur=_short(nouvelle_valeur),
                detail=_short(detail),
                adresse_ip=_short(ip, 45),
            ))
            db.commit()
        finally:
            db.close()

    except Exception:
        # An unwritable audit trail is a serious operational problem, but it must
        # not fail the user's action. Surface it in the application log instead.
        logger.exception("audit: failed to record %s", action)


def query(
    db,
    action: str | None = None,
    user_id: int | None = None,
    employe_id: int | None = None,
    depuis: date | None = None,
    limit: int = 200,
) -> list[dict]:
    """Read the trail, most recent first."""
    from models.models import AuditLog

    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if employe_id:
        q = q.filter(AuditLog.cible_employe_id == employe_id)
    if depuis:
        q = q.filter(AuditLog.date_action >= depuis)

    rows = q.order_by(AuditLog.date_action.desc()).limit(min(limit, 1000)).all()
    return [{
        "audit_id": r.audit_id,
        "date_action": r.date_action.isoformat() if r.date_action else None,
        "username": r.username,
        "role": r.role,
        "action": r.action,
        "entite": r.entite,
        "entite_id": r.entite_id,
        "cible_employe_id": r.cible_employe_id,
        "ancienne_valeur": r.ancienne_valeur,
        "nouvelle_valeur": r.nouvelle_valeur,
        "detail": r.detail,
        "adresse_ip": r.adresse_ip,
    } for r in rows]
