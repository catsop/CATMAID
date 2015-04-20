/*
 * This file reflects the current state of the segmentation schema template.
 * When updating the segmentation schema via migrations, also update this file
 * to reflect those changes and instantiate_segmentation.sql to reflect changes
 * relevant to new segmentation stacks.
 *
 * The initial version of this schema for migration 0033 is in
 * segmentation_schema_initial.sql.
 */

CREATE SCHEMA IF NOT EXISTS segstack_template;
SET search_path TO segstack_template,public;

/* Spatial division */

CREATE TABLE block (
  id serial PRIMARY KEY,
  slices_flag boolean NOT NULL,
  segments_flag boolean NOT NULL,
  coordinate_x integer NOT NULL,
  coordinate_y integer NOT NULL,
  coordinate_z integer NOT NULL,
  UNIQUE (coordinate_x, coordinate_y, coordinate_z),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE INDEX block_coordinate_x ON block USING btree (coordinate_x);
CREATE INDEX block_coordinate_y ON block USING btree (coordinate_y);
CREATE INDEX block_coordinate_z ON block USING btree (coordinate_z);

CREATE TABLE core (
  id serial PRIMARY KEY,
  solution_set_flag boolean NOT NULL,
  coordinate_x integer NOT NULL,
  coordinate_y integer NOT NULL,
  coordinate_z integer NOT NULL,
  UNIQUE (coordinate_x, coordinate_y, coordinate_z),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE INDEX core_coordinate_x ON core USING btree (coordinate_x);
CREATE INDEX core_coordinate_y ON core USING btree (coordinate_y);
CREATE INDEX core_coordinate_z ON core USING btree (coordinate_z);

/* Slices */

CREATE TABLE slice (
  id bigint PRIMARY KEY,
  section integer NOT NULL,
  min_x integer NOT NULL,
  min_y integer NOT NULL,
  max_x integer NOT NULL,
  max_y integer NOT NULL,
  ctr_x double precision NOT NULL,
  ctr_y double precision NOT NULL,
  value double precision NOT NULL,
  size integer NOT NULL,
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE INDEX slice_max_x ON slice USING btree (max_x);
CREATE INDEX slice_max_y ON slice USING btree (max_y);
CREATE INDEX slice_min_x ON slice USING btree (min_x);
CREATE INDEX slice_min_y ON slice USING btree (min_y);
CREATE INDEX slice_section ON slice USING btree (section);

CREATE TABLE slice_block_relation (
  block_id integer NOT NULL REFERENCES block(id) DEFERRABLE INITIALLY IMMEDIATE,
  slice_id bigint NOT NULL REFERENCES slice(id) DEFERRABLE INITIALLY IMMEDIATE,
  PRIMARY KEY (block_id, slice_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE treenode_slice (
  treenode_id integer NOT NULL REFERENCES treenode(id) DEFERRABLE INITIALLY IMMEDIATE,
  slice_id bigint NOT NULL REFERENCES slice(id) DEFERRABLE INITIALLY IMMEDIATE,
  PRIMARY KEY (treenode_id, slice_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE slice_conflict (
  id bigserial PRIMARY KEY,
  slice_a_id bigint NOT NULL REFERENCES slice(id) DEFERRABLE INITIALLY IMMEDIATE,
  slice_b_id bigint NOT NULL REFERENCES slice(id) DEFERRABLE INITIALLY IMMEDIATE,
  UNIQUE (slice_a_id, slice_b_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE conflict_clique (
  id bigserial PRIMARY KEY,
  maximal_clique boolean NOT NULL,
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE conflict_clique_edge (
  conflict_clique_id bigint NOT NULL REFERENCES conflict_clique(id) DEFERRABLE INITIALLY IMMEDIATE,
  slice_conflict_id bigint NOT NULL REFERENCES slice_conflict(id) DEFERRABLE INITIALLY IMMEDIATE,
  PRIMARY KEY (conflict_clique_id, slice_conflict_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE block_conflict_relation (
  block_id integer NOT NULL REFERENCES block(id) DEFERRABLE INITIALLY IMMEDIATE,
  slice_conflict_id integer NOT NULL REFERENCES slice_conflict(id) DEFERRABLE INITIALLY IMMEDIATE,
  PRIMARY KEY (block_id, slice_conflict_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

/* Segment */

CREATE TABLE segment (
  id bigint PRIMARY KEY,
  section_sup integer NOT NULL,
  min_x integer NOT NULL,
  min_y integer NOT NULL,
  max_x integer NOT NULL,
  max_y integer NOT NULL,
  ctr_x double precision NOT NULL,
  ctr_y double precision NOT NULL,
  type integer NOT NULL,
  cost double precision,
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE INDEX segment_section_sup ON segment USING btree (section_sup);

CREATE TABLE segment_slice (
  slice_id bigint NOT NULL REFERENCES slice(id) DEFERRABLE INITIALLY IMMEDIATE,
  segment_id bigint NOT NULL REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE,
  direction boolean NOT NULL,
  PRIMARY KEY (slice_id, segment_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE segment_features (
  segment_id bigint PRIMARY KEY REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE,
  features double precision[] NOT NULL,
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE segment_block_relation (
  block_id integer NOT NULL REFERENCES block(id) DEFERRABLE INITIALLY IMMEDIATE,
  segment_id bigint NOT NULL REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE,
  PRIMARY KEY (block_id, segment_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

/* Solution */

CREATE TABLE solution (
  id serial PRIMARY KEY,
  core_id integer NOT NULL REFERENCES core(id) DEFERRABLE INITIALLY IMMEDIATE,
  creation_time timestamp with time zone NOT NULL DEFAULT now(),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE assembly_equivalence (
  id serial PRIMARY KEY,
  skeleton_id integer REFERENCES class_instance(id) DEFERRABLE INITIALLY IMMEDIATE,
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE assembly (
  id serial PRIMARY KEY,
  equivalence_id integer REFERENCES assembly_equivalence(id) DEFERRABLE INITIALLY IMMEDIATE,
  solution_id integer NOT NULL REFERENCES solution(id) DEFERRABLE INITIALLY IMMEDIATE,
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE assembly_relation (
  id serial PRIMARY KEY,
  assembly_a_id integer NOT NULL REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE,
  assembly_b_id integer NOT NULL REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE,
  relation assemblyrelation NOT NULL,
  UNIQUE (assembly_a_id, assembly_b_id, relation),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE solution_precedence (
  core_id integer PRIMARY KEY REFERENCES core(id) DEFERRABLE INITIALLY IMMEDIATE,
  solution_id integer NOT NULL REFERENCES solution(id) DEFERRABLE INITIALLY IMMEDIATE,
  UNIQUE (solution_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE segment_solution (
  segment_id bigint NOT NULL REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE,
  solution_id integer NOT NULL REFERENCES solution(id) DEFERRABLE INITIALLY IMMEDIATE,
  assembly_id integer REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE,
  PRIMARY KEY (segment_id, solution_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE solution_constraint (
  id serial PRIMARY KEY,
  user_id integer NOT NULL REFERENCES auth_user(id) DEFERRABLE INITIALLY IMMEDIATE,
  creation_time timestamp with time zone NOT NULL,
  edition_time timestamp with time zone NOT NULL,
  skeleton_id integer REFERENCES class_instance(id) DEFERRABLE INITIALLY IMMEDIATE,
  relation constraintrelation NOT NULL,
  value double precision NOT NULL,
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE block_constraint_relation (
  block_id integer NOT NULL REFERENCES block(id) DEFERRABLE INITIALLY IMMEDIATE,
  constraint_id integer NOT NULL REFERENCES solution_constraint(id) DEFERRABLE INITIALLY IMMEDIATE,
  PRIMARY KEY (block_id, constraint_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE constraint_segment_relation (
  constraint_id integer NOT NULL REFERENCES solution_constraint(id) DEFERRABLE INITIALLY IMMEDIATE,
  segment_id bigint NOT NULL REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE,
  coefficient double precision NOT NULL,
  PRIMARY KEY (constraint_id, segment_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

CREATE TABLE correction (
  constraint_id integer NOT NULL REFERENCES solution_constraint(id) DEFERRABLE INITIALLY IMMEDIATE,
  mistake_id bigint NOT NULL REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE,
  PRIMARY KEY (constraint_id, mistake_id),
  CHECK (false) NO INHERIT -- prevent any rows populating this table
) WITH (
  OIDS=FALSE
);

RESET search_path;
