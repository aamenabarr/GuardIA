import express from 'express';
import { getComplexityMetrics } from '../controllers/complexity';

const router = express.Router();

router.get("/", getComplexityMetrics);

export default router;
