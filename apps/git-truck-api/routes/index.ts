import express from 'express';
import reposRouter from './repo';
import contributionsRouter from './contributions';
import complexityMetricRouter from './complexity';
import tempRepoMiddleware from '../middleware/tempRepo';
import cleanupMiddleware from '../middleware/cleanup';

const router = express.Router();

router.use("/repo", tempRepoMiddleware, cleanupMiddleware, reposRouter);
router.use("/contributions", tempRepoMiddleware, cleanupMiddleware, contributionsRouter);
router.use("/complexity", tempRepoMiddleware, cleanupMiddleware, complexityMetricRouter);

export default router;
