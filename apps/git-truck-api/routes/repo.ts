import express from 'express';
import { getRepoData } from '../controllers/repo';

const router = express.Router();

router.get("/", getRepoData);

export default router;
