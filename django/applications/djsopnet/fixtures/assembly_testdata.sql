TRUNCATE
    segstack_2.block, segstack_2.core,
    segstack_2.slice, segstack_2.slice_conflict, segstack_2.slice_block_relation,
    segstack_2.conflict_clique, segstack_2.conflict_clique_edge,
    segstack_2.segment, segstack_2.segment_slice, segstack_2.segment_block_relation,
    segstack_2.solution_assembly, segstack_2.solution, segstack_2.solution_precedence,
    segstack_2.assembly, segstack_2.assembly_segment CASCADE;

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

/**
 * 10000xx <> 10010xx continue and are compatible in precedent solution.
 * 10002xx and 10003xx (slice) conflict with 10001xx. 10003xx is in an old solution.
 * 10001xx <> 10012xx conflict in precedent solution.
 * Like 10001xx, 10004xx branches at the core 000,001 boundary. However in this
 * case the assembly in 001 chooses the branch, while 000 does not, so:
 * 10004xx <> 10014xx continue and conflict in the precedent solution.
 */

-- slice IDs are of the form [1][core_x][core_y][core_z][arbitrary ID][section # (2 digits)]
INSERT INTO segstack_2.slice
(id, section, min_x, min_y, max_x, max_y, ctr_x, ctr_y, value, size)
-- CORE (0, 0, 0)
SELECT 1000000 + sect, sect, 0, 0, 10, 10, 5, 5, 1, 1
FROM generate_series(0, 9) AS sect
UNION
SELECT 1000100 + sect, sect, 0, 0, 10, 10, 5, 5, 1, 1
FROM generate_series(0, 9) AS sect
UNION
SELECT 1000400 + sect, sect, 0, 0, 10, 10, 5, 5, 1, 1
FROM generate_series(0, 9) AS sect
-- CORE (0, 0, 1)
UNION
SELECT 1001000 + sect, sect, 0, 0, 10, 10, 5, 5, 1, 1
FROM generate_series(10, 19) AS sect
UNION
SELECT 1001200 + sect, sect, 0, 0, 10, 10, 5, 5, 1, 1
FROM generate_series(10, 19) AS sect
UNION
SELECT 1001400 + sect, sect, 0, 0, 10, 10, 5, 5, 1, 1
FROM generate_series(10, 19) AS sect;

INSERT INTO segstack_2.slice
(id, section, min_x, min_y, max_x, max_y, ctr_x, ctr_y, value, size) VALUES
(1000209, 9, 0, 0, 10, 10, 5, 5, 1, 1),
(1000509, 9, 0, 0, 10, 10, 5, 5, 1, 1);

INSERT INTO segstack_2.slice_conflict
(id, slice_a_id, slice_b_id) VALUES
(1000109, 1000109, 1000209),
(1000409, 1000409, 1000509);

INSERT INTO segstack_2.conflict_clique
(id, maximal_clique) VALUES
(1000109, TRUE),
(1000409, TRUE);

INSERT INTO segstack_2.conflict_clique_edge
(conflict_clique_id, slice_conflict_id) VALUES
(1000109, 1000109),
(1000409, 1000409);

INSERT INTO segstack_2.slice_block_relation
(block_id, slice_id)
SELECT 000, s.id FROM segstack_2.slice s WHERE s.id BETWEEN 1000000 AND 1000999
UNION
SELECT 001, s.id FROM segstack_2.slice s WHERE s.id BETWEEN 1001000 AND 1001999;

-- segment IDs are of the form [1][core_x][core_y][core_z][arbitrary ID][section sup (2 digits)]
INSERT INTO segstack_2.segment
(id, section_sup, min_x, min_y, max_x, max_y, type)
-- CORE (0, 0, 0)
SELECT 1000000 + sect, sect, 0, 0, 10, 10, (CASE WHEN sect > 0 THEN 1 ELSE 0 END)
FROM generate_series(0, 9) AS sect
UNION
SELECT 1000100 + sect, sect, 0, 0, 10, 10, (CASE WHEN sect > 0 THEN 1 ELSE 0 END)
FROM generate_series(0, 9) AS sect
UNION
SELECT 1000400 + sect, sect, 0, 0, 10, 10, (CASE WHEN sect > 0 THEN 1 ELSE 0 END)
FROM generate_series(0, 9) AS sect
-- CORE (0, 0, 1)
UNION
SELECT 1001000 + sect, sect, 0, 0, 10, 10, (CASE WHEN sect < 20 THEN 1 ELSE 0 END)
FROM generate_series(10, 20) AS sect
UNION
SELECT 1001200 + sect, sect, 0, 0, 10, 10, (CASE WHEN sect < 20 THEN 1 ELSE 0 END)
FROM generate_series(10, 20) AS sect
UNION
SELECT 1001400 + sect, sect, 0, 0, 10, 10, (CASE WHEN sect < 20 THEN 1 ELSE 0 END)
FROM generate_series(10, 20) AS sect;

INSERT INTO segstack_2.segment
(id, section_sup, min_x, min_y, max_x, max_y, type) VALUES
(1000209, 9, 0, 0, 10, 10, 1), -- Unused continuation
(1000309, 9, 0, 0, 10, 10, 2), -- Unused branch
(1001110, 10, 0, 0, 10, 10, 1), -- Unused continuation
(1001310, 10, 0, 0, 10, 10, 2), -- Unused branch
(1000509, 9, 0, 0, 10, 10, 1), -- Unused continuation
(1000609, 9, 0, 0, 10, 10, 2), -- Unused branch
(1001510, 10, 0, 0, 10, 10, 1), -- Unused continuation
(1001610, 10, 0, 0, 10, 10, 1); -- Used branch

INSERT INTO segstack_2.segment_slice
(slice_id, segment_id, direction)
-- direction is TRUE == left
SELECT 1000000 + sect, 1000000 + sect + dir, dir = 1
FROM generate_series(0, 8) AS sect, generate_series(0, 1) AS dir
UNION
SELECT 1000100 + sect, 1000100 + sect + dir, dir = 1
FROM generate_series(0, 8) AS sect, generate_series(0, 1) AS dir
UNION
SELECT 1000400 + sect, 1000400 + sect + dir, dir = 1
FROM generate_series(0, 8) AS sect, generate_series(0, 1) AS dir
UNION
SELECT 1001000 + sect, 1001000 + sect + dir, dir = 1
FROM generate_series(10, 19) AS sect, generate_series(0, 1) AS dir
UNION
SELECT 1001200 + sect, 1001200 + sect + dir, dir = 1
FROM generate_series(10, 19) AS sect, generate_series(0, 1) AS dir
UNION
SELECT 1001400 + sect, 1001400 + sect + dir, dir = 1
FROM generate_series(10, 19) AS sect, generate_series(0, 1) AS dir;

INSERT INTO segstack_2.segment_slice
(slice_id, segment_id, direction) VALUES
(1000009, 1000009, FALSE),
(1000109, 1000109, FALSE),
(1000108, 1000209, TRUE),  -- Unused continuation
(1000209, 1000209, FALSE),
(1000108, 1000309, TRUE),  -- Unused branch
(1000109, 1000309, FALSE),
(1000209, 1000309, FALSE),
(1000009, 1001010, TRUE),
(1000109, 1001110, TRUE),
(1000209, 1001210, TRUE),
(1000109, 1001310, TRUE),
(1000209, 1001310, TRUE),
(1000409, 1000409, FALSE),
(1000408, 1000509, TRUE),  -- Unused continuation
(1000509, 1000509, FALSE),
(1000408, 1000609, TRUE),  -- Unused branch
(1000409, 1000609, TRUE),
(1000509, 1000609, TRUE),
(1000409, 1001410, TRUE),  -- Unused continuation
(1000509, 1001510, TRUE),  -- Unused continuation
(1001410, 1001510, FALSE),
(1000409, 1001610, TRUE),  -- Used branch
(1000509, 1001610, TRUE),
(1001410, 1001610, FALSE);

INSERT INTO segstack_2.segment_block_relation
(block_id, segment_id)
SELECT 000, s.id FROM segstack_2.segment s WHERE s.id BETWEEN 1000000 AND 1000999
UNION
SELECT 001, s.id FROM segstack_2.segment s WHERE s.id BETWEEN 1001000 AND 1001999;

-- solution ids are of the form [core_x][core_y][core_z][sequence #]
INSERT INTO segstack_2.solution
(id, core_id) VALUES
(0000, 000), -- A bad, non-precedent solution
(0001, 000),
(0011, 001);

INSERT INTO segstack_2.solution_precedence
(core_id, solution_id) VALUES
(000, 0001),
(001, 0011);

-- assembly IDs are fo the form 1[core_x][core_y][core_z][arbitrary ID related to segments][sequence #]
INSERT INTO segstack_2.assembly
(id, core_id, hash) VALUES
(1000001, 000, 1000001),
(1000101, 000, 1000101), -- Bad assembly from solution 000
(1000102, 000, 1000102), -- revised version from solution 001
(1000401, 000, 1000401),
(1001001, 001, 1001001),
(1001201, 001, 1001201),
(1001401, 001, 1001401);

INSERT INTO segstack_2.solution_assembly
(solution_id, assembly_id) VALUES
(0000, 1000001),
(0000, 1000101),
(0001, 1000001),
(0001, 1000102),
(0001, 1000401),
(0011, 1001001),
(0011, 1001201),
(0011, 1001401);

INSERT INTO segstack_2.assembly_segment
(segment_id, assembly_id)
SELECT s.id, 1000001 FROM segstack_2.segment s
WHERE s.id BETWEEN 1000000 AND 1000099
UNION
SELECT s.id, 1000101 FROM segstack_2.segment s
WHERE s.id BETWEEN 1000100 AND 1000108
UNION
SELECT s.id, 1000102 FROM segstack_2.segment s
WHERE s.id BETWEEN 1000100 AND 1000199
UNION
SELECT s.id, 1000401 FROM segstack_2.segment s
WHERE s.id BETWEEN 1000400 AND 1000499
UNION
SELECT s.id, 1001001 FROM segstack_2.segment s
WHERE s.id BETWEEN 1001000 AND 1001099
UNION
SELECT s.id, 1001201 FROM segstack_2.segment s
WHERE s.id BETWEEN 1001200 AND 1001299
UNION
SELECT s.id, 1001401 FROM segstack_2.segment s
WHERE s.id BETWEEN 1001411 AND 1001499;

INSERT INTO segstack_2.assembly_segment
(segment_id, assembly_id) VALUES
(1000309, 1000101),
(1001610, 1001401);
