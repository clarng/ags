require('dotenv').config();

const { neon } = require('@neondatabase/serverless');

const DATABASE_URL = "postgresql://neondb_owner:npg_5ynuXGxJTtg7@ep-mute-king-a5329b7b-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

const sql = neon(DATABASE_URL ?? process.env.DATABASE_URL);

async function getPgVersion() {
  const result = await sql`SELECT version()`;
  console.log(result[0]);
}

async function listDatabases() {
  try {
    // Query to list all databases in the PostgreSQL instance
    const result = await sql`
      SELECT datname as database_name
      FROM pg_database
      WHERE datistemplate = false
      ORDER BY datname;
    `;
    return result;
  } catch (error) {
    console.error('Error listing databases:', error);
    throw error;
  }
}

async function queryTable(query = 'SELECT *') {
  try {
    const result = await sql`${sql.raw(query)}`;
    return {
      columns: Object.keys(result[0] || {}),
      rows: result
    };
  } catch (error) {
    console.error('Error executing query:', error);
    throw error;
  }
}

// Example usage
async function main() {
  try {
    console.log('PostgreSQL Version:');
    await getPgVersion();
    
    console.log('\nAvailable Databases:');
    const databases = await listDatabases();
    console.log(databases);
  } catch (error) {
    console.error('Error:', error);
  }
}

module.exports = {
  getPgVersion,
  listDatabases,
  queryTable
};

main();
