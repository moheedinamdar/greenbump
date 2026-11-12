from marshmallow import Schema, ValidationError, fields, validates
from marshmallow.experimental.context import Context


class UserSchema(Schema):
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    role = fields.Str(load_default="viewer")
    active = fields.Bool(dump_default=True)
    display = fields.Method("get_display", dump_only=True)

    def get_display(self, obj):
        prefix = Context.get({}).get("prefix", "")
        return f"{prefix}{obj['name']}"

    @validates("name")
    def validate_name(self, value, **kwargs):
        if len(value.strip()) < 2:
            raise ValidationError("Name is too short.")


def load_user(data):
    return UserSchema().load(data)


def dump_user(user, prefix=""):
    with Context({"prefix": prefix}):
        return UserSchema().dump(user)
