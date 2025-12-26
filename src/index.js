const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const facultyRoutes = require('./routes/facultyRoutes');

dotenv.config();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/faculty', facultyRoutes);

// Root Endpoint
app.get('/', (req, res) => {
    res.send('GuruSetu Backend API is running...');
});

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});