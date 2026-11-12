from marshmallow import Schema, ValidationError, fields, validates


class UserSchema(Schema):
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    role = fields.Str(missing="viewer")
    active = fields.Bool(default=True)
    display = fields.Method("get_display", dump_only=True)

    def get_display(self, obj):
        prefix = self.context.get("prefix", "")
        return f"{prefix}{obj['name']}"

    @validates("name")
    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise ValidationError("Name is too short.")


def load_user(data):
    return UserSchema().load(data)


def dump_user(user, prefix=""):
    return UserSchema(context={"prefix": prefix}).dump(user)
