CREATE OR REPLACE VIEW eis_fire_lf_perimeter_nrt_latest AS
SELECT DISTINCT ON (fireid) 
    fireid, t, region, duration, farea, meanfrp, fperim, n_pixels, n_newpixels, pixden, primarykey, geometry
FROM public.eis_fire_lf_perimeter_nrt
ORDER BY fireid, t DESC;