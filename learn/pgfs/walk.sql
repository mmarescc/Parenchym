CREATE MATERIALIZED VIEW pympgfs.mv_nodepath AS
  WITH RECURSIVE parentnode AS
  (
    -- non-recursive term
    SELECT
      id, parent_id, name,
      name::text AS path,
      0 AS lvl
    FROM pympgfs.node
    WHERE parent_id IS NULL

    UNION ALL

    -- recursive term
    SELECT
      n.id, n.parent_id, n.name,
      pn.path || '/' || n.name AS path,
      pn.lvl + 1 AS lvl
    FROM pympgfs.node AS n
    JOIN parentnode as pn ON n.parent_id=pn.id
  )
  SELECT * FROM parentnode
  ORDER BY path
;

CREATE INDEX mv_nodepath_path_ix ON pympgfs.mv_nodepath (path);
