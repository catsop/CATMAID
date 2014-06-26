-- This function translates the Sopnet generated data into CATMAID treenodes,
-- which will be marked as created by the user ID passed as parameter. The
-- target representation is a tree, while the source is a graph. Therefore,
-- some edged have to be cut while translating.
CREATE OR REPLACE FUNCTION get_solution_graph(integer, integer)
RETURNS void AS $$
DECLARE
  solution_id ALIAS FOR $1;
  sopnet_user_id ALIAS FOR $2;
	end_segment RECORD;
	visited_end_nodes integer[];
BEGIN
	-- Find all end segments that are part of a solution of any code and iterate
	-- them, skip already visited.
	FOR end_segment IN SELECT *	FROM djsopnet_segmentsolution so, djsopnet_segment se
				WHERE so.solution = true AND se.type = 0 AND so.segment_id = se.id
  LOOP
		-- Add this end segment to the list of visited nodes
		visited_end_nodes = array_append(visited_end_nodes, end_segment.id);

		-- Create A Common Table Expression to find all nodes of a graph in a
		-- solution. These nodes are represented as the center of each of its slices. An edge is
		-- defined by two segments that connected through a slice.

		-- This is done by starting from a segment of type 0 (an end segment, links
		-- always only to slice a; for every graph there are always at least two) and
		-- following its linked slices.

		WITH RECURSIVE search_slices(parent_hash, slice_hash, ctr1_x, ctr1_y,
						ctr1_z, path, cycle) AS (
				-- Start from current end segment, representing one graph, and get the
				-- slice connected to it.
				SELECT NULL, sl.hash_value, sl.ctr_x, sl.ctr_y, sl.section,
							 ARRAY[se.id], false
						FROM end_segment se, djsopnet_slice sl
						WHERE se.slice_a_id = sl.hash_value

			-- We don't want duplicates, therefore use UNION instead of UNION ALL
			UNION (

				-- Find all slices that are connected to the parent though a type 1
				-- segment (continuation) or a the first link of a type 2 segment
				-- (branch)
				SELECT ss.slice_hash, se.slice_b_id, sl.ctr_x, sl.ctr_y, sl.section,
							 path || se.id, se.id = ANY(path)
						FROM djsopnet_segmentsolution so, djsopnet_segment se,
                 djsopnet_slice sl, search_slices ss
						WHERE so.solution = true AND so.segment_id = se.id AND
								  ss.slice_hash = se.slice_a_id AND NOT cylce
				-- Combiene with all slices that are connected to the parent though the
				-- secod link of a type 2 segment (branch).
				UNION SELECT ss.slice_hash, se.slice_c_id, sl.ctr_x, sl.ctr_y, sl.section,
							 			 path || se.id, se.id = ANY(path)
						FROM djsopnet_segmentsolution so, djsopnet_segment se,
                 djsopnet_slice sl, search_slices ss
						WHERE so.solution = true AND so.segment_id = se.id AND
								  ss.slice_hash = se.slice_a_id AND NOT cylce
				-- Combine with all slices that are connected to the parent as either
				-- first or second link of a brach, but in reverse direction.
				UNION SELECT ss.slice_hash, se.slice_a_id, sl.ctr_x, sl.ctr_y, sl.section,
							 			 path || se.id, se.id = ANY(path)
						FROM djsopnet_segmentsolution so, djsopnet_segment se,
                 djsopnet_slice sl, search_slices ss
						WHERE so.solution = true AND so.segment_id = se.id AND NOT cycle AND
								  (ss.slice_hash = se.slice_b_id OR ss.slice_hash = se.slice_c_id)
				)
		)
		-- This yields all nodes of a graph and the ID of its parent. These need to
		-- be inserted in the treenode table now. To do this, the cooridnates are
		-- required to be transformed into project space (which dependes on the
		-- orientation of the stack).
		INSERT INTO catmaid_skeleton_intersections (child_id, parent_id, intersection)
			VALUES (id, parent_id, node.location);
	  SELECT * FROM search_slices;
	END LOOP;

	RETURN;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION stack_to_project_xy(integer, integer)
RETURNS void AS $$
DECLARE
BEGIN
	RETURN;
END;
$$ LANGUAGE plpgsql;
