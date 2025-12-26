const express = require('express');
const router = express.Router();
const facultyController = require('../controllers/facultyController');

// GET /api/faculty
router.get('/', facultyController.getAllFaculty);
// POST /api/faculty/:id/request
router.post('/:id/request', facultyController.requestUpdate);
// PUT /api/faculty/:id/status (Optional: for manual updates via API)
router.put('/:id/status', facultyController.updateStatus);

module.exports = router;