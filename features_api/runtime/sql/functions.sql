DO $$
BEGIN
  IF EXISTS (
    SELECT
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name   = 'eis_fire_lf_perimeter_nrt'
  )
  AND NOT EXISTS (
    SELECT
    FROM information_schema.views
    WHERE table_schema = 'pg_temp'
      AND table_name   = 'eis_fire_lf_perimeter_nrt_latest'
  )
  THEN
    CREATE VIEW eis_fire_lf_perimeter_nrt_latest AS
    SELECT DISTINCT ON (fireid) 
        fireid, t, region, duration, farea, meanfrp, fperim, n_pixels, n_newpixels, pixden, primarykey, geometry
    FROM public.eis_fire_lf_perimeter_nrt
    ORDER BY fireid, t DESC;
  END IF;
END $$;
