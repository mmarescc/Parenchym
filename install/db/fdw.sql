/*
CREATE FOREIGN TABLE odbc_table (
	db_id integer, 
	db_name varchar(255)
) 
	SERVER odbc_server
	OPTIONS (
		database 'atrial_devel',
		schema 'atrial', 
		table 'atrial', 
		sql_query 'select id, name from atrial.role',
		sql_count 'select count(id) from atrial.role',
		db_id 'id', 
		db_name 'name'
	);
*/

/*
CREATE SERVER delbaeth_server 
FOREIGN DATA WRAPPER odbc_fdw 
OPTIONS (dsn 'delbaeth');
*/

CREATE FOREIGN TABLE nw_products_table (
	id integer, 
	name varchar(255)
) 
	SERVER delbaeth_server
	OPTIONS (
		database 'Northwind',
		schema 'dbo', 
		table 'Products', 
		sql_query 'select ProductID, ProductName from dbo.Products',
		sql_count 'select count(ProductID) from dbo.Products',
		id 'ProductID', 
		name 'ProductName'
	);

/*
CREATE USER MAPPING FOR postgres
SERVER delbaeth_server
OPTIONS (username 'sa', password 'QaY123');
*/
