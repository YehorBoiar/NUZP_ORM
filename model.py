from datatypes import Field


class ModelMeta(type):
    """
    Metaclass to register model fields.
    """
    def __new__(cls, name, bases, attrs):
        fields = {}
        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value

        attrs["_fields"] = fields
        return super().__new__(cls, name, bases, attrs)

