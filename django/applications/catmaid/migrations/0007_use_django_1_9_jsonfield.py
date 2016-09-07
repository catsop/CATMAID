# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-10 05:34
from __future__ import unicode_literals

import django.contrib.auth.models
import django.contrib.postgres.fields.jsonb
from django.db import migrations


# DDL triggers aren't yet implemented for CATMAID's history tracking. Therefore,
# the history updates have to be implemented manually. Additionally, there is no
# need to create a new history table column for this type conversion and an
# in-place type update is appropriate.

update_clientdata_history = """
    DO $$
    BEGIN
    EXECUTE format(
        'ALTER TABLE %1$s '
        'ALTER COLUMN value '
        'TYPE jsonb '
        'USING value::jsonb',
        history_table_name('client_data'::regclass));
    END
    $$;
"""

downgrade_clientdata_history = """
    DO $$
    BEGIN
    EXECUTE format(
        'ALTER TABLE %1$s '
        'ALTER COLUMN value '
        'TYPE text '
        'USING value::text',
        history_table_name('client_data'::regclass));
    END
    $$;
"""

class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0007_alter_validators_add_error_messages'),
        ('catmaid', '0006_add_history_table_support'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clientdata',
            name='value',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}),
        ),
        migrations.RunSQL(update_clientdata_history,
            downgrade_clientdata_history)
    ]
