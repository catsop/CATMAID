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

-- slice IDs are of the form [1][core_x][core_y][core_z][arbitrary ID][section # (2 digits)]
INSERT INTO segstack_2.slice
(id, section, min_x, min_y, max_x, max_y, ctr_x, ctr_y, value, size)
-- CORE (0, 0, 0)
SELECT 1000000 + sect, sect, 0, 0, 10, 10, 5, 5, 1, 1
FROM generate_series(0, 9) AS sect
UNION
SELECT 1000100 + sect, sect, 0, 0, 10, 10, 5, 5, 1, 1
FROM generate_series(0, 9) AS sect;

INSERT INTO segstack_2.slice
(id, section, min_x, min_y, max_x, max_y, ctr_x, ctr_y, value, size) VALUES
(1000209, 9, 0, 0, 10, 10, 5, 5, 1, 1);

INSERT INTO segstack_2.slice_conflict
(id, slice_a_id, slice_b_id) VALUES
(1000109, 1000109, 1000209);

INSERT INTO segstack_2.conflict_clique
(id, maximal_clique) VALUES
(1000109, TRUE);

INSERT INTO segstack_2.conflict_clique_edge
(conflict_clique_id, slice_conflict_id) VALUES
(1000109, 1000109);

INSERT INTO segstack_2.slice_block_relation
(block_id, slice_id)
SELECT 000, s.id FROM segstack_2.slice s WHERE s.id BETWEEN 1000000 AND 1000999;

-- slice IDs are of the form [1][core_x][core_y][core_z][arbitrary ID][section sup (2 digits)]
INSERT INTO segstack_2.segment
(id, section_sup, min_x, min_y, max_x, max_y, ctr_x, ctr_y, type)
-- CORE (0, 0, 0)
SELECT 1000000 + sect, sect, 0, 0, 10, 10, 5, 5, (CASE WHEN sect > 0 THEN 1 ELSE 0 END)
FROM generate_series(0, 9) AS sect
UNION
SELECT 1000100 + sect, sect, 0, 0, 10, 10, 5, 5, (CASE WHEN sect > 0 THEN 1 ELSE 0 END)
FROM generate_series(0, 9) AS sect;

INSERT INTO segstack_2.segment
(id, section_sup, min_x, min_y, max_x, max_y, ctr_x, ctr_y, type) VALUES
(1000209, 9, 0, 0, 10, 10, 5, 5, 1), -- Unused continuation
(1000309, 9, 0, 0, 10, 10, 5, 5, 2); -- Unused branch

INSERT INTO segstack_2.segment_slice
(slice_id, segment_id, direction)
-- direction is TRUE == left
SELECT 1000000 + sect, 1000000 + sect + dir, dir = 1
FROM generate_series(0, 8) AS sect, generate_series(0, 1) AS dir
UNION
SELECT 1000100 + sect, 1000100 + sect + dir, dir = 1
FROM generate_series(0, 8) AS sect, generate_series(0, 1) AS dir;

INSERT INTO segstack_2.segment_slice
(slice_id, segment_id, direction) VALUES
(1000009, 1000009, FALSE),
(1000109, 1000109, FALSE),
(1000108, 1000209, TRUE),  -- Unused continuation
(1000209, 1000209, FALSE),
(1000108, 1000309, TRUE),  -- Unused branch
(1000109, 1000309, FALSE),
(1000209, 1000309, FALSE);

INSERT INTO segstack_2.segment_block_relation
(block_id, segment_id)
SELECT 000, s.id FROM segstack_2.segment s WHERE s.id BETWEEN 1000000 AND 1000999;

-- solution ids are of the form [core_x][core_y][core_z][sequence #]
INSERT INTO segstack_2.solution
(id, core_id) VALUES
(0000, 000), -- A bad, non-precedent solution
(0001, 000);

INSERT INTO segstack_2.solution_precedence
(core_id, solution_id) VALUES
(000, 0001);

INSERT INTO segstack_2.segment_solution
(segment_id, solution_id)
SELECT s.id, 0000 FROM segstack_2.segment s
WHERE s.id BETWEEN 1000000 AND 1000099
   OR s.id BETWEEN 1000100 AND 1000108
UNION
SELECT s.id, 0001 FROM segstack_2.segment s
WHERE s.id BETWEEN 1000000 AND 1000099
   OR s.id BETWEEN 1000100 AND 1000199;

INSERT INTO segstack_2.segment_solution
(segment_id, solution_id) VALUES
(1000309, 0000);
