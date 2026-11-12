[out:json][timeout:180];
area["ISO3166-1"="IN"][admin_level=2]->.in;
(
  way["landuse"="landfill"](area.in);
  relation["landuse"="landfill"](area.in);
  way["amenity"="waste_disposal"]["waste"!="trash"](area.in);
);
out tags geom;
