# Import all models here so that Base.metadata has them registered
# before Alembic runs migrations.

from app.db.base_class import Base  # noqa
from app.modules.users.models import User  # noqa
from app.modules.auth.models import OTPState  # noqa
