const express = require('express');
const router = express.Router();
const { listDatabases, queryTable } = require('./db');

// API endpoint to list databases
router.get('/databases', async (req, res) => {
    try {
        const databases = await listDatabases();
        res.json(databases);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// API endpoint to run queries
router.post('/query', async (req, res) => {
    try {
        const { database, query } = req.body;
        if (!database || !query) {
            return res.status(400).json({ error: 'Database and query are required' });
        }
        
        const result = await queryTable(query);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

module.exports = router; 