DO $$
BEGIN
  IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'eis_fire_lf_perimeter_nrt') THEN
    CREATE OR REPLACE VIEW eis_fire_lf_perimeter_nrt_latest AS
    SELECT DISTINCT ON (fireid) 
        fireid, t, region, duration, farea, meanfrp, fperim, n_pixels, n_newpixels, pixden, primarykey, geometry
    FROM public.eis_fire_lf_perimeter_nrt
    ORDER BY fireid, t DESC;
  END IF;
END $$;