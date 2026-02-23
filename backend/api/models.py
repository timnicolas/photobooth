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


def init_db():
    with db:
        db.create_tables([User, Mask, Photo], safe=True)
