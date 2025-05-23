require('dotenv').config();

const { neon } = require('@neondatabase/serverless');

const database = "neondb"
const DATABASE_URL = `postgresql://neondb_owner:npg_5ynuXGxJTtg7@ep-mute-king-a5329b7b-pooler.us-east-2.aws.neon.tech/${database}?sslmode=require`

const sql = neon(DATABASE_URL ?? process.env.DATABASE_URL);

async function getPgVersion() {
  try {
    const result = await sql`SELECT version()`;
    return result[0];
  } catch (error) {
    console.error('Error getting PostgreSQL version:', error);
    throw new Error('Failed to connect to database');
  }
}

async function listDatabases() {
  try {
    // Query to list all databases in the PostgreSQL instance
    const result = await sql`
      SELECT datname as database_name
      FROM pg_database
      WHERE datistemplate = false
      AND datname <> 'postgres'
      ORDER BY datname;
    `;
    return result;
  } catch (error) {
    console.error('Error listing databases:', error);
    throw new Error('Failed to list databases');
  }
}

async function checkDatabase(database) {
  if (!database) {
    console.error('no db provided', error);
    throw new Error('no db provided');
  }

  result = await sql`SELECT current_database() as db;`
  db = result[0]['db']
  if (db != database) {
    throw new Error('wrong db'); 
  }
}

async function listTables(database) {
  try {
    await checkDatabase(database);
    
    // Query to list all tables in the current database
    result = await sql`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public'
      ORDER BY table_name;
    `;
    return result;
  } catch (error) {
    console.error('Error listing tables:', error);
    throw new Error('Failed to list tables');
  }
}

async function queryTable(query, database, table) {
  const sql = neon(DATABASE_URL ?? process.env.DATABASE_URL);
  try {
    if (!query) {
      throw new Error('Query is required');
    }

    await checkDatabase(database);

    const result = await sql(query);
    
    // If no results, return empty structure
    if (!result || result.length === 0) {
      return {
        columns: [],
        rows: []
      };
    }

    return {
      columns: Object.keys(result[0]),
      rows: result
    };
  } catch (error) {
    console.error('Error executing query:', error);
    throw new Error(`Query execution failed: ${error.message}`);
  }
}

module.exports = {
  getPgVersion,
  listDatabases,
  listTables,
  queryTable
}; 