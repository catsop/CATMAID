# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.db import models, migrations
from datetime import datetime
import django.core.validators
import django.contrib.gis.db.models.fields
import catmaid.control.user
from django.conf import settings
from django.utils import timezone


# This is the database schema of CATSOP/CATMAID 2015.12.21 without owner information.
initial_schema = """
--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;


CREATE TYPE public.assemblyrelation AS ENUM
   ('Compatible',
    'Conflict',
    'Continuation');

CREATE TYPE public.constraintrelation AS ENUM
   ('LessEqual',
    'Equal',
    'GreaterEqual');


SET default_tablespace = '';

SET default_with_oids = false;



CREATE SEQUENCE public.segmentation_configuration_id_seq
  INCREMENT 1
  MINVALUE 1
  MAXVALUE 9223372036854775807
  START 1
  CACHE 1;

-- Table: public.segmentation_configuration

-- DROP TABLE public.segmentation_configuration;

CREATE TABLE public.segmentation_configuration
(
  id integer NOT NULL DEFAULT nextval('segmentation_configuration_id_seq'::regclass),
  project_id integer NOT NULL,
  CONSTRAINT segmentation_configuration_pkey PRIMARY KEY (id),
  CONSTRAINT project_id_refs_id_03c89645 FOREIGN KEY (project_id)
      REFERENCES public.project (id) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
)
WITH (
  OIDS=FALSE
);

-- Index: public.segmentation_configuration_project_id

-- DROP INDEX public.segmentation_configuration_project_id;

CREATE INDEX segmentation_configuration_project_id
  ON public.segmentation_configuration
  USING btree
  (project_id);



CREATE SEQUENCE public.segmentation_stack_id_seq
  INCREMENT 1
  MINVALUE 1
  MAXVALUE 9223372036854775807
  START 1
  CACHE 1;

-- Table: public.segmentation_stack

-- DROP TABLE public.segmentation_stack;

CREATE TABLE public.segmentation_stack
(
  id integer NOT NULL DEFAULT nextval('segmentation_stack_id_seq'::regclass),
  configuration_id integer NOT NULL,
  project_stack_id integer NOT NULL,
  type character varying(128) NOT NULL,
  CONSTRAINT segmentation_stack_pkey PRIMARY KEY (id),
  CONSTRAINT configuration_id_refs_id_75614f11 FOREIGN KEY (configuration_id)
      REFERENCES public.segmentation_configuration (id) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
  CONSTRAINT project_stack_id_refs_id_26f35206 FOREIGN KEY (project_stack_id)
      REFERENCES public.project_stack (id) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
)
WITH (
  OIDS=FALSE
);

-- Index: public.segmentation_stack_configuration_id

-- DROP INDEX public.segmentation_stack_configuration_id;

CREATE INDEX segmentation_stack_configuration_id
  ON public.segmentation_stack
  USING btree
  (configuration_id);

-- Index: public.segmentation_stack_project_stack_id

-- DROP INDEX public.segmentation_stack_project_stack_id;

CREATE INDEX segmentation_stack_project_stack_id
  ON public.segmentation_stack
  USING btree
  (project_stack_id);



-- Table: public.segmentation_block_info

-- DROP TABLE public.segmentation_block_info;

CREATE TABLE public.segmentation_block_info
(
  num_x integer NOT NULL,
  num_y integer NOT NULL,
  num_z integer NOT NULL,
  block_dim_y integer NOT NULL,
  block_dim_x integer NOT NULL,
  block_dim_z integer NOT NULL,
  core_dim_y integer NOT NULL,
  core_dim_x integer NOT NULL,
  core_dim_z integer NOT NULL,
  scale integer NOT NULL,
  configuration_id integer NOT NULL,
  CONSTRAINT segmentation_block_info_pkey PRIMARY KEY (configuration_id),
  CONSTRAINT configuration_id_refs_id_7b7730b5 FOREIGN KEY (configuration_id)
      REFERENCES public.segmentation_configuration (id) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
)
WITH (
  OIDS=FALSE
);



CREATE SEQUENCE public.segmentation_feature_name_id_seq
  INCREMENT 1
  MINVALUE 1
  MAXVALUE 9223372036854775807
  START 1
  CACHE 1;

-- Table: public.segmentation_feature_name

-- DROP TABLE public.segmentation_feature_name;

CREATE TABLE public.segmentation_feature_name
(
  id integer NOT NULL DEFAULT nextval('segmentation_feature_name_id_seq'::regclass),
  name character varying(128) NOT NULL,
  CONSTRAINT djsopnet_featurename_pkey PRIMARY KEY (id)
)
WITH (
  OIDS=FALSE
);



-- Table: public.segmentation_feature_info

-- DROP TABLE public.segmentation_feature_info;

CREATE TABLE public.segmentation_feature_info
(
  size integer NOT NULL,
  name_ids integer[] NOT NULL,
  weights double precision[] NOT NULL,
  segmentation_stack_id integer NOT NULL,
  CONSTRAINT segmentation_feature_info_pkey PRIMARY KEY (segmentation_stack_id),
  CONSTRAINT segmentation_stack_id_refs_id_9790148b FOREIGN KEY (segmentation_stack_id)
      REFERENCES public.segmentation_stack (id) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
)
WITH (
  OIDS=FALSE
);


--
-- Name: public; Type: ACL; Schema: -; Owner: -
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

"""

initial_state_operations = [
    migrations.CreateModel(
        name='FeatureName',
        fields=[
            ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=128)),
        ],
        options={
            'db_table': 'segmentation_feature_name',
        },
    ),
    migrations.CreateModel(
        name='SegmentationConfiguration',
        fields=[
            ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ],
        options={
            'db_table': 'segmentation_configuration',
        },
    ),
    migrations.CreateModel(
        name='SegmentationStack',
        fields=[
            ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('type', models.CharField(max_length=128)),
        ],
        options={
            'db_table': 'segmentation_stack',
        },
    ),
    migrations.CreateModel(
        name='BlockInfo',
        fields=[
            ('configuration', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='block_info', serialize=False, to='djsopnet.SegmentationConfiguration')),
            ('scale', models.IntegerField(default=0, help_text=b'\n        Zoom level for segmentation data relative to raw stack.')),
            ('block_dim_x', models.IntegerField(default=256)),
            ('block_dim_y', models.IntegerField(default=256)),
            ('block_dim_z', models.IntegerField(default=16)),
            ('core_dim_x', models.IntegerField(default=1)),
            ('core_dim_y', models.IntegerField(default=1)),
            ('core_dim_z', models.IntegerField(default=1)),
            ('num_x', models.IntegerField(default=0)),
            ('num_y', models.IntegerField(default=0)),
            ('num_z', models.IntegerField(default=0)),
        ],
        options={
            'db_table': 'segmentation_block_info',
        },
    ),
    migrations.CreateModel(
        name='FeatureInfo',
        fields=[
            ('segmentation_stack', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='djsopnet.SegmentationStack')),
            ('size', models.IntegerField(default=0)),
            ('name_ids', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), size=None)),
            ('weights', django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), size=None)),
        ],
        options={
            'db_table': 'segmentation_feature_info',
        },
    ),
    migrations.AddField(
        model_name='segmentationstack',
        name='configuration',
        field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='djsopnet.SegmentationConfiguration'),
    ),
    migrations.AddField(
        model_name='segmentationstack',
        name='project_stack',
        field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='catmaid.ProjectStack'),
    ),
    migrations.AddField(
        model_name='segmentationconfiguration',
        name='project',
        field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='catmaid.Project'),
    ),
]


def load_initial_segmentation_schema(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    with open(os.path.join(os.path.dirname(__file__), '..', 'sql', 'segmentation_schema_initial.sql'), 'r') as sqlfile:
            cursor.execute(sqlfile.read())


class Migration(migrations.Migration):
    """Migrate the database to the state of the last South migration"""

    initial = True

    dependencies = [
        ('catmaid', '0013_add_missing_tnci_and_cnci_indices'),
    ]

    operations = [
        migrations.RunSQL(initial_schema, None, initial_state_operations),
        migrations.RunPython(load_initial_segmentation_schema, None),
    ]
