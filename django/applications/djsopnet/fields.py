from django.db import models

from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^djsopnet\.fields\.ConstraintRelationEnumField"])

class EnumField(models.Field):
    """Enumeration field type for PostgreSQL.

    See http://wiki.postgresql.org/images/0/0b/Postgresql_django_extensions.pdf
    """
    description = 'enumerated type'

    def __init__(self, *args, **kwargs):
        self.enum = kwargs['enum']
        del kwargs['enum']
        super(EnumField, self).__init__(*args, **kwargs)

    def db_type(self, connection):
        return self.enum

class ConstraintRelationEnumField(EnumField):
    description = 'enumerated relation type for constriant equations'

    enum_choices = (
        ('LessEqual', 'Less than or equal to'),
        ('Equal', 'Equal to'),
        ('GreaterEqual', 'Greater than or equal to'))

    def __init__(self, *args, **kwargs):
        self.enum = 'constraintrelation'
        kwargs['enum'] = self.enum
        kwargs['choices'] = ConstraintRelationEnumField.enum_choices
        super(ConstraintRelationEnumField, self).__init__(*args, **kwargs)