import datetime

from peewee import (
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    Model,
    SqliteDatabase,
)

from api.config import Config

db = SqliteDatabase(Config.DATABASE_PATH)


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    mail = CharField(unique=True)
    firstname = CharField()
    lastname = CharField()
    password = CharField()  # stocké hashé (werkzeug)
    is_admin = BooleanField(default=False)

    class Meta:
        table_name = "users"


class Mask(BaseModel):
    filename = CharField()  # basename UUID, ex: "a1b2c3.png"
    label = CharField()
    orientation = CharField(default="both")  # "portrait", "landscape", "both"
    is_active = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "masks"


class Photo(BaseModel):
    filename = CharField()
    mask = ForeignKeyField(Mask, null=True, backref="photos", on_delete="SET NULL")
    captured_at = DateTimeField(default=datetime.datetime.now)
    printed = BooleanField(default=False)

    class Meta:
        table_name = "photos"


class AppSettings(BaseModel):
    """Paramètres globaux de l'application — une seule ligne (singleton)."""
    allow_no_mask = BooleanField(default=True)

    class Meta:
        table_name = "app_settings"

    @classmethod
    def get_instance(cls):
        """Retourne l'unique ligne de paramètres, en la créant si nécessaire."""
        instance, _ = cls.get_or_create(id=1, defaults={"allow_no_mask": True})
        return instance


def init_db():
    with db:
        db.create_tables([User, Mask, Photo, AppSettings], safe=True)
        # Migration : ajout de la colonne orientation si absente
        try:
            db.execute_sql("ALTER TABLE masks ADD COLUMN orientation VARCHAR(16) DEFAULT 'both'")
        except Exception:
            pass  # Colonne déjà présente
        # Initialise les paramètres par défaut si absents
        AppSettings.get_instance()
