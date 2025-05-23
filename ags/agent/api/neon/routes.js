const express = require('express');
const router = express.Router();
const { listDatabases, queryTable, getPgVersion, listTables } = require('./db');

// API endpoint to get PostgreSQL version
router.get('/version', async (req, res) => {
    try {
        const version = await getPgVersion();
        res.json({ version });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// API endpoint to list databases
router.get('/databases', async (req, res) => {
    try {
        const databases = await listDatabases();
        res.json(databases);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// API endpoint to list tables
router.get('/tables', async (req, res) => {
    try {
        const { database } = req.query;

        if (!database) {
            return res.status(400).json({ error: 'database is required' });
        }

        const tables = await listTables(database);
        res.json(tables);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// API endpoint to run queries
router.post('/query', async (req, res) => {
    try {
        const { database, query, table } = req.body;
        
        // Validate input
        if (!query) {
            return res.status(400).json({ error: 'Query is required' });
        }

        // Execute query with optional database and table selection
        const result = await queryTable(query, database, table);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

module.exports = router; 