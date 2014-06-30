create foreign table mysql_table (
  account_key integer,
  account_email varchar(255),
  account_password varchar(255)
) server alchemy_srv options (
  tablename 'oe_account',
  db_url 'mysql+mysqlconnector://root:root@localhost/ccp_portal'
);
