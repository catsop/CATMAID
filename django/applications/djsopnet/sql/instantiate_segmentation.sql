/*
 * Creates an inherited copy of the segmentation schema in segstack_template
 * in the current schema search_path, including indices and foreign keys.
 */

-- CREATE SCHEMA segstack_test;
-- SET search_path TO segstack_test,public;

/* Spatial division */

CREATE TABLE block
    (LIKE segstack_template.block INCLUDING INDEXES)
    INHERITS (segstack_template.block);

CREATE TABLE core
    (LIKE segstack_template.core INCLUDING INDEXES)
    INHERITS (segstack_template.core);

/* Slice */

CREATE TABLE slice
    (LIKE segstack_template.slice INCLUDING INDEXES)
    INHERITS (segstack_template.slice);

CREATE TABLE slice_block_relation
    (LIKE segstack_template.slice_block_relation INCLUDING INDEXES,
      FOREIGN KEY (slice_id) REFERENCES slice(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (block_id) REFERENCES block(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.slice_block_relation);

CREATE TABLE treenode_slice
    (LIKE segstack_template.treenode_slice INCLUDING INDEXES,
      FOREIGN KEY (treenode_id) REFERENCES treenode(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (slice_id) REFERENCES slice(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.treenode_slice);

CREATE TABLE slice_conflict
    (LIKE segstack_template.slice_conflict INCLUDING INDEXES,
      FOREIGN KEY (slice_a_id) REFERENCES slice(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (slice_b_id) REFERENCES slice(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.slice_conflict);

CREATE TABLE conflict_clique
    (LIKE segstack_template.conflict_clique INCLUDING INDEXES)
    INHERITS (segstack_template.conflict_clique);

CREATE TABLE conflict_clique_edge
    (LIKE segstack_template.conflict_clique_edge INCLUDING INDEXES,
      FOREIGN KEY (conflict_clique_id) REFERENCES conflict_clique(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (slice_conflict_id) REFERENCES slice_conflict(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.conflict_clique_edge);

CREATE TABLE block_conflict_relation
    (LIKE segstack_template.block_conflict_relation INCLUDING INDEXES,
      FOREIGN KEY (slice_conflict_id) REFERENCES slice_conflict(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (block_id) REFERENCES block(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.block_conflict_relation);

/* Segment */

CREATE TABLE segment
    (LIKE segstack_template.segment INCLUDING INDEXES)
    INHERITS (segstack_template.segment);

CREATE TABLE segment_slice
    (LIKE segstack_template.segment_slice INCLUDING INDEXES,
      FOREIGN KEY (slice_id) REFERENCES slice(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (segment_id) REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.segment_slice);

CREATE TABLE segment_features
    (LIKE segstack_template.segment_features INCLUDING INDEXES,
      FOREIGN KEY (segment_id) REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.segment_features);

CREATE TABLE segment_block_relation
    (LIKE segstack_template.segment_block_relation INCLUDING INDEXES,
      FOREIGN KEY (segment_id) REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (block_id) REFERENCES block(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.segment_block_relation);

/* Solution */

CREATE TABLE solution
    (LIKE segstack_template.solution INCLUDING INDEXES,
      FOREIGN KEY (core_id) REFERENCES core(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.solution);

CREATE TABLE assembly_equivalence
    (LIKE segstack_template.assembly_equivalence INCLUDING INDEXES,
      FOREIGN KEY (skeleton_id) REFERENCES class_instance(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.assembly_equivalence);

CREATE TABLE assembly
    (LIKE segstack_template.assembly INCLUDING INDEXES,
      FOREIGN KEY (equivalence_id) REFERENCES assembly_equivalence(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (core_id) REFERENCES core(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.assembly);

CREATE TABLE assembly_relation
    (LIKE segstack_template.assembly_relation INCLUDING INDEXES,
      FOREIGN KEY (assembly_a_id) REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (assembly_b_id) REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.assembly_relation);

CREATE TABLE solution_precedence
    (LIKE segstack_template.solution_precedence INCLUDING INDEXES,
      FOREIGN KEY (core_id) REFERENCES core(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (solution_id) REFERENCES solution(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.solution_precedence);

CREATE TABLE solution_assembly
    (LIKE segstack_template.solution_assembly INCLUDING INDEXES,
      FOREIGN KEY (solution_id) REFERENCES solution(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (assembly_id) REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.solution_assembly);

CREATE TABLE assembly_segment
    (LIKE segstack_template.assembly_segment INCLUDING INDEXES,
      FOREIGN KEY (assembly_id) REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (segment_id) REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.assembly_segment);

CREATE TABLE solution_constraint
    (LIKE segstack_template.solution_constraint INCLUDING INDEXES,
      FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (skeleton_id) REFERENCES class_instance(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.solution_constraint);

CREATE TABLE block_constraint_relation
    (LIKE segstack_template.block_constraint_relation INCLUDING INDEXES,
      FOREIGN KEY (constraint_id) REFERENCES solution_constraint(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (block_id) REFERENCES block(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.block_constraint_relation);

CREATE TABLE constraint_segment_relation
    (LIKE segstack_template.constraint_segment_relation INCLUDING INDEXES,
      FOREIGN KEY (constraint_id) REFERENCES solution_constraint(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (segment_id) REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.constraint_segment_relation);

CREATE TABLE correction
    (LIKE segstack_template.correction INCLUDING INDEXES,
      FOREIGN KEY (constraint_id) REFERENCES solution_constraint(id) DEFERRABLE INITIALLY IMMEDIATE,
      FOREIGN KEY (mistake_id) REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE)
    INHERITS (segstack_template.correction);

CREATE OR REPLACE RULE solution_precedence_on_duplicate_update
    AS ON INSERT TO solution_precedence
    WHERE EXISTS (SELECT 1 FROM solution_precedence WHERE core_id = NEW.core_id)
    DO INSTEAD UPDATE solution_precedence
    SET solution_id = NEW.solution_id WHERE core_id = NEW.core_id;

-- RESET search_path;
