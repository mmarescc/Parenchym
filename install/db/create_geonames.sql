CREATE SCHEMA geonames;

CREATE TABLE geonames.geoname
(
  geonameid integer not null primary key,
  name varchar(200),
  asciiname varchar(200),
  alternatenames text,
  latitude double precision,
  longitude double precision,
  feature_class char(1),
  feature_code varchar(10),
  country_code char(2),
  cc2 varchar(60),
  admin1_code varchar(20),
  admin2_code varchar(80),
  admin3_code varchar(20),
  admin4_code varchar(20),
  population bigint,
  elevation varchar(255),
  dem text,
  timezone varchar(40),
  mtime date
);

-- \copy geonames.geoname from allCountries.txt


create table geonames.hierarchy
(
  id1 integer,
  id2 integer,
  adm varchar(255)
);

-- \copy geonames.hierarchy from hierarchy.txt


create table geonames.continent
(
  code char(2),
  name varchar(32),
  id integer
);
INSERT INTO geonames.continent values ('AF', 'Africa',        6255146);
INSERT INTO geonames.continent values ('AS', 'Asia',          6255147);
INSERT INTO geonames.continent values ('EU', 'Europe',        6255148);
INSERT INTO geonames.continent values ('NA', 'North America', 6255149);
INSERT INTO geonames.continent values ('OC', 'Oceania',       6255151);
INSERT INTO geonames.continent values ('SA', 'South America', 6255150);
INSERT INTO geonames.continent values ('AN', 'Antarctica',    6255152);


select * from geonames.hierarchy
where id1 = 6255146
;

-- -----------------------------------------------------------------


-- Level 1: Europe
select
  n.*
from geonames.geoname n
  where n.geonameid = 6255148
;
select
  n.*
from geonames.geoname n
  inner join geonames.hierarchy h on h.id2 = n.geonameid
where id1 = 6255148
;

-- Level 2: Federal Republic of Germany
select
  n.*
from geonames.geoname n
  where n.geonameid = 2921044
;
select
  n.*
from geonames.geoname n
  inner join geonames.hierarchy h on h.id2 = n.geonameid
where id1 = 2921044
;

-- Level 3: Freistaat Bayern
select
  n.*
from geonames.geoname n
  where n.geonameid = 2951839
;
select
  n.*
from geonames.geoname n
  inner join geonames.hierarchy h on h.id2 = n.geonameid
where id1 = 2951839
;

-- Level 4: Upper Franconia
select
  n.*
from geonames.geoname n
  where n.geonameid = 2860681
;
select
  n.*
from geonames.geoname n
  inner join geonames.hierarchy h on h.id2 = n.geonameid
where id1 = 2860681
;

-- Level 5: Kreisfreie Stadt Bayreuth
select
  n.*
from geonames.geoname n
  where n.geonameid = 3220845
;
select
  n.*
from geonames.geoname n
  inner join geonames.hierarchy h on h.id2 = n.geonameid
where id1 = 3220845
;

-- Level 6: Bayreuth
select
  n.*
from geonames.geoname n
  where n.geonameid = 6556726
;
select
  n.*
from geonames.geoname n
  inner join geonames.hierarchy h on h.id2 = n.geonameid
where id1 = 6556726
;


-- -----------------------------------------------------------------

-- Level 1: Africa
select
  n.*
from geonames.geoname n
  where n.geonameid = 6255146
;
select
  n.*
from geonames.geoname n
  inner join geonames.hierarchy h on h.id2 = n.geonameid
where id1 = 6255146
;

-- Level 2: Congo
select
  n.*
from geonames.geoname n
  where n.geonameid = 2260494
;
select
  n.*
from geonames.geoname n
  inner join geonames.hierarchy h on h.id2 = n.geonameid
where id1 = 2260494
;

-- Level 3: Plateaux
select
  n.*
from geonames.geoname n
  where n.geonameid = 2255422
;
select
  n.*
from geonames.geoname n
  inner join geonames.hierarchy h on h.id2 = n.geonameid
where id1 = 2255422
;

-- Level 4: Lekana
select
  n.*
from geonames.geoname n
  where n.geonameid = 7870663
;
select
  n.*
from geonames.geoname n
  inner join geonames.hierarchy h on h.id2 = n.geonameid
where id1 = 7870663
;
