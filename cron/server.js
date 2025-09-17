const express = require('express');
const cron = require('node-cron');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3000;


// Cron job running every 5 minutes
cron.schedule('*/5 * * * *', () => {
    console.log('Running health check...');
    axios.get('https://ticket-sale-2.onrender.com/health')
        .then(response => {
            console.log('Health check success:', response.status);
        })
        .catch(error => {
            console.error('Health check failed:', error.message);
        });
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
