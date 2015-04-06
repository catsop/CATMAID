-- core and block ids are of the form xyz
INSERT INTO segstack_2.block
(id, slices_flag, segments_flag, coordinate_x, coordinate_y, coordinate_z)
SELECT 100*x + 10*y + z, TRUE, TRUE, x, y, z
FROM generate_series(0,1) AS x,
     generate_series(0,1) AS y,
     generate_series(0,1) AS z;

INSERT INTO segstack_2.core
(id, solution_set_flag, coordinate_x, coordinate_y, coordinate_z)
SELECT 100*x + 10*y + z, TRUE, x, y, z
FROM generate_series(0,1) AS x,
     generate_series(0,1) AS y,
     generate_series(0,1) AS z;

INSERT INTO segstack_2.slice
(id, section, min_x, min_y, max_x, max_y, ctr_x, ctr_y, value, size) VALUES
-- CORE (0, 0, 0)
(1000, 0, 0, 0, 10, 10, 5, 5, 1, 1),
(1001, 1, 0, 0, 10, 10, 5, 5, 1, 1),
(1002, 2, 0, 0, 10, 10, 5, 5, 1, 1),
(1003, 3, 0, 0, 10, 10, 5, 5, 1, 1),
(1004, 4, 0, 0, 10, 10, 5, 5, 1, 1),
(1005, 5, 0, 0, 10, 10, 5, 5, 1, 1),
(1006, 6, 0, 0, 10, 10, 5, 5, 1, 1),
(1007, 7, 0, 0, 10, 10, 5, 5, 1, 1),
(1008, 8, 0, 0, 10, 10, 5, 5, 1, 1),
(1009, 9, 0, 0, 10, 10, 5, 5, 1, 1);

INSERT INTO segstack_2.slice_block_relation
(block_id, slice_id)
SELECT 000, s.id FROM segstack_2.slice s WHERE s.id BETWEEN 1000 and 1999;

INSERT INTO segstack_2.segment
(id, section_sup, min_x, min_y, max_x, max_y, ctr_x, ctr_y, type) VALUES
-- CORE (0, 0, 0)
(1000, 0, 0, 0, 10, 10, 5, 5, 0),
(1001, 1, 0, 0, 10, 10, 5, 5, 1),
(1002, 2, 0, 0, 10, 10, 5, 5, 1),
(1003, 3, 0, 0, 10, 10, 5, 5, 1),
(1004, 4, 0, 0, 10, 10, 5, 5, 1),
(1005, 5, 0, 0, 10, 10, 5, 5, 1),
(1006, 6, 0, 0, 10, 10, 5, 5, 1),
(1007, 7, 0, 0, 10, 10, 5, 5, 1),
(1008, 8, 0, 0, 10, 10, 5, 5, 1),
(1009, 9, 0, 0, 10, 10, 5, 5, 1);

INSERT INTO segstack_2.segment_slice
(slice_id, segment_id, direction) VALUES
-- direction is TRUE == left
(1000, 1000, FALSE),
(1000, 1001, TRUE),
(1001, 1001, FALSE),
(1001, 1002, TRUE),
(1002, 1002, FALSE),
(1002, 1003, TRUE),
(1003, 1003, FALSE),
(1003, 1004, TRUE),
(1004, 1004, FALSE),
(1004, 1005, TRUE),
(1005, 1005, FALSE),
(1005, 1006, TRUE),
(1006, 1006, FALSE),
(1006, 1007, TRUE),
(1007, 1007, FALSE),
(1007, 1008, TRUE),
(1008, 1008, FALSE),
(1008, 1009, TRUE),
(1009, 1009, FALSE);

INSERT INTO segstack_2.segment_block_relation
(block_id, segment_id)
SELECT 000, s.id FROM segstack_2.segment s WHERE s.id BETWEEN 1000 AND 1999;

-- solution ids are of the form [core_x][core_y][core_z][sequence #]
INSERT INTO segstack_2.solution
(id, core_id) VALUES
(0000, 000);

INSERT INTO segstack_2.solution_precedence
(core_id, solution_id) VALUES
(000, 0000);

INSERT INTO segstack_2.segment_solution
(segment_id, solution_id)
SELECT s.id, 0000 FROM segstack_2.segment s WHERE s.id BETWEEN 1000 AND 1999;
